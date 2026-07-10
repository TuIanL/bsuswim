from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.session import SessionLocal
from app.models import (
    AnalysisResult,
    AnalysisTask,
    AnalysisTaskStatus,
    NormalizedAnnotation,
    ReportMetadata,
    SessionVideo,
    TrainingSession,
    TrainingSessionStatus,
)
from app.schemas import AnalysisSubmit, ModelAnalysisRequest, ModelAnalysisResult
from app.services.annotation_quality.legacy import normalize_quality_payload
from app.services.annotation_quality.models import AnalysisQualitySummary
from app.services.annotation_quality.validator import AnnotationQualityValidator
from app.services.annotation_quality.provider import YamlQualityProfileProvider
from app.services.model_client import ModelServiceClient, ModelServiceError
from app.services.report_builder import build_report_data
from app.services.storage import playback_url

import os


class AnnotationQualityBlockedError(Exception):
    def __init__(self, quality: dict):
        self.quality = quality
        issues = quality.get("issues", [])
        blockers = [i for i in issues if i.get("blocking")]
        message = "标注质量不足以开始分析"
        if blockers:
            message = f"存在 {len(blockers)} 个必须修复的问题"
        super().__init__(message)


def _get_validator() -> AnnotationQualityValidator:
    profiles_dir = os.path.join(os.path.dirname(__file__), "annotation_quality", "profiles")
    provider = YamlQualityProfileProvider(profiles_dir)
    return AnnotationQualityValidator(profile_provider=provider)


def _ensure_quality_gate(
    annotation: NormalizedAnnotation,
    acknowledge_warnings: bool = False,
    revision_locked: int | None = None,
) -> dict:
    report = normalize_quality_payload(annotation.quality)
    status = report.status

    # ── revision drift detection ──
    if revision_locked is not None and annotation.revision != revision_locked:
        raise AnnotationQualityBlockedError({
            "status": "invalid",
            "summary": {"blocking_count": 1, "error_count": 1, "warning_count": 0, "info_count": 0},
            "issues": [{
                "code": "ANNOTATION_REVISION_DRIFT",
                "category": "context",
                "severity": "error",
                "blocking": True,
                "message": f"标注 revision 从 {revision_locked} 变为 {annotation.revision}，请重新提交",
                "user_message": "标注已被重新解析，请重新提交分析任务。",
            }],
        })

    if status == "invalid":
        raise AnnotationQualityBlockedError(report.model_dump(mode="json"))

    if status == "warning" and not acknowledge_warnings:
        raise AnnotationQualityBlockedError(report.model_dump(mode="json"))

    return report.model_dump(mode="json")


def task_actions(task: AnalysisTask) -> list[str]:
    if task.status == AnalysisTaskStatus.COMPLETED:
        return ["workspace", "report"]
    if task.status == AnalysisTaskStatus.FAILED:
        return ["retry", "details"]
    return ["details"]


def create_analysis_task(db: Session, payload: AnalysisSubmit) -> AnalysisTask:
    session = db.get(TrainingSession, payload.session_id)
    if not session:
        raise ValueError("训练记录不存在")

    # ── resolve annotation ──
    annotation: NormalizedAnnotation | None = None
    if payload.normalized_annotation_id:
        annotation = db.get(NormalizedAnnotation, payload.normalized_annotation_id)
        if not annotation or annotation.session_video.session_id != payload.session_id:
            raise ValueError("指定的标准化标注不存在或不属于当前训练记录")
    else:
        side_video = next(
            (v for v in session.videos if hasattr(v, 'view_type') and v.view_type.value == "side"),
            None,
        )
        if side_video:
            annotation = db.scalars(
                select(NormalizedAnnotation)
                .where(NormalizedAnnotation.session_video_id == side_video.id)
                .order_by(NormalizedAnnotation.revision.desc())
            ).first()

    # ── quality gate ──
    quality_snapshot: dict | None = None
    if annotation:
        quality_snapshot = _ensure_quality_gate(annotation, payload.acknowledge_quality_warnings)

    # ── create task ──
    request_payload = build_model_request_payload(db, payload.session_id)
    task = AnalysisTask(
        session_id=payload.session_id,
        status=AnalysisTaskStatus.QUEUED,
        progress=5,
        stage="queued",
    )
    db.add(task)
    db.flush()
    request_payload["task_id"] = task.id
    request_payload["analysis_input"] = {
        "type": "normalized_annotation",
        "annotation_id": annotation.id if annotation else None,
        "annotation_revision": annotation.revision if annotation else None,
        "annotation_quality_snapshot": quality_snapshot,
    }
    if quality_snapshot:
        report = normalize_quality_payload(quality_snapshot)
        degraded_modules = [
            mk for mk, mr in report.module_readiness.items()
            if mr.status in ("degraded", "blocked")
        ]
        if degraded_modules:
            request_payload["analysis_input"]["degraded_modules"] = degraded_modules

    task.request_payload = request_payload

    if session:
        session.status = TrainingSessionStatus.ANALYZING
        db.add(session)

    db.commit()
    db.refresh(task)
    return task


def build_model_request_payload(db: Session, session_id: int) -> dict:
    session = db.get(
        TrainingSession,
        session_id,
        options=[
            joinedload(TrainingSession.athlete),
            joinedload(TrainingSession.videos).joinedload(SessionVideo.video_file),
        ],
    )
    if not session:
        raise ValueError("训练记录不存在")
    if not session.videos:
        raise ValueError("训练记录尚未绑定视频")

    return {
        "task_id": 0,
        "session_id": session.id,
        "athlete": {
            "id": session.athlete.id,
            "name": session.athlete.name,
            "gender": session.athlete.gender,
            "level": session.athlete.level,
        },
        "session": {
            "id": session.id,
            "title": session.title,
                "stroke_type": session.stroke_type.value if hasattr(session.stroke_type, "value") else session.stroke_type,
            "distance_m": session.distance_m,
            "pool_length_m": float(session.pool_length_m) if session.pool_length_m is not None else None,
            "session_date": session.session_date.isoformat() if session.session_date else None,
        },
        "videos": [
            {
                "video_file_id": link.video_file_id,
                    "view_type": link.view_type.value if hasattr(link.view_type, "value") else link.view_type,
                "video_url": playback_url(link.video_file.stored_filename),
                "video_path": link.video_file.storage_path,
                "fps": float(link.fps) if link.fps is not None else None,
                "resolution": link.resolution,
                "sync_offset_ms": link.sync_offset_ms,
            }
            for link in session.videos
        ],
        "callback_url": f"/api/v1/analysis/{{task_id}}/result",
        "schema_version": "analysis.request.v1",
    }


async def run_analysis_task(task_id: int) -> None:
    db = SessionLocal()
    try:
        task = db.get(
            AnalysisTask,
            task_id,
            options=[joinedload(AnalysisTask.session).joinedload(TrainingSession.athlete)],
        )
        if not task:
            return

        _set_task_state(db, task, AnalysisTaskStatus.PROCESSING, "model_inference", 35)
        client = ModelServiceClient()
        request_payload = dict(task.request_payload)
        request_payload["task_id"] = task.id
        request_payload["callback_url"] = f"/api/v1/analysis/{task.id}/result"
        result = await client.analyze(ModelAnalysisRequest.model_validate(request_payload))

        save_analysis_result(db, task, result)
    except ModelServiceError as exc:
        _mark_failed(db, task_id, str(exc))
    except Exception as exc:
        _mark_failed(db, task_id, f"分析任务执行失败: {exc}")
    finally:
        db.close()


def save_analysis_result(db: Session, task: AnalysisTask, result: ModelAnalysisResult) -> AnalysisResult | None:
    if result.status == "failed":
        task.status = AnalysisTaskStatus.FAILED
        task.stage = "failed"
        task.error_message = result.error_message or "模型服务返回失败状态"
        if task.session:
            task.session.status = TrainingSessionStatus.FAILED
            db.add(task.session)
        db.add(task)
        db.commit()
        db.refresh(task)
        return task.result

    _set_task_state(db, task, AnalysisTaskStatus.RESULT_SAVING, "result_saving", 80)

    existing = db.scalar(select(AnalysisResult).where(AnalysisResult.task_id == task.id))
    if existing:
        analysis_result = existing
        analysis_result.schema_version = result.schema_version
        analysis_result.detections = result.detections
        analysis_result.keypoint_frames = result.keypoint_frames
        analysis_result.phases = result.phases
        analysis_result.metrics = result.metrics
        analysis_result.diagnostics = result.diagnostics
        analysis_result.raw_result = result.model_dump()
    else:
        analysis_result = AnalysisResult(
            task_id=task.id,
            schema_version=result.schema_version,
            detections=result.detections,
            keypoint_frames=result.keypoint_frames,
            phases=result.phases,
            metrics=result.metrics,
            diagnostics=result.diagnostics,
            raw_result=result.model_dump(),
        )

    db.add(analysis_result)
    db.flush()

    report = db.scalar(select(ReportMetadata).where(ReportMetadata.session_id == task.session_id))
    report_data = build_report_data(task, analysis_result)
    if report:
        report.task_id = task.id
        report.source = "model_service_mock"
        report.report_data = report_data
    else:
        report = ReportMetadata(
            session_id=task.session_id,
            task_id=task.id,
            source="model_service_mock",
            report_data=report_data,
        )
    db.add(report)

    if task.session:
        task.session.status = TrainingSessionStatus.COMPLETED
        db.add(task.session)

    _set_task_state(db, task, AnalysisTaskStatus.COMPLETED, "completed", 100, completed=True)
    db.refresh(analysis_result)
    return analysis_result


def _set_task_state(
    db: Session,
    task: AnalysisTask,
    status: AnalysisTaskStatus,
    stage: str,
    progress: int,
    completed: bool = False,
) -> None:
    task.status = status
    task.stage = stage
    task.progress = progress
    task.error_message = None
    if completed:
        task.completed_at = datetime.utcnow()
    db.add(task)
    db.commit()
    db.refresh(task)


def _mark_failed(db: Session, task_id: int, message: str) -> None:
    task = db.get(AnalysisTask, task_id, options=[joinedload(AnalysisTask.session)])
    if not task:
        return
    task.status = AnalysisTaskStatus.FAILED
    task.stage = "failed"
    task.progress = max(task.progress, 1)
    task.error_message = message
    if task.session:
        task.session.status = TrainingSessionStatus.FAILED
        db.add(task.session)
    db.add(task)
    db.commit()
