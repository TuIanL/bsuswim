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
    ViewType,
)
from app.schemas import AnalysisSubmit, ModelAnalysisRequest, ModelAnalysisResult
from app.services.annotation_quality.legacy import normalize_quality_payload
from app.services.annotation_quality.models import AnalysisQualitySummary
from app.services.annotation_quality.validator import AnnotationQualityValidator
from app.services.annotation_quality.provider import YamlQualityProfileProvider
from app.services.model_client import ModelServiceError
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


class AnnotationSelectionRequiredError(Exception):
    def __init__(self, candidate_ids: list[int]):
        self.candidate_ids = candidate_ids
        super().__init__("存在可用标准化标注，请明确选择")


class AnnotationInputUnavailableError(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__("没有可用的标准化标注")


class AnalysisTaskAlreadyActiveError(Exception):
    """同一训练记录已有活跃的 annotation_kinematics 任务（design Decision 17）。"""

    def __init__(self, existing_task_id: int):
        self.existing_task_id = existing_task_id
        super().__init__("当前训练记录已有二维运动学分析任务正在执行")


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


def task_actions(task: AnalysisTask, error_code: str | None = None) -> list[str]:
    from app.services.analysis_pipelines.errors import recovery_policy_for

    effective_error = error_code if error_code is not None else task.error_code
    # completed 但合成出错误码（如 REPORT_METADATA_MISSING）视为可恢复失败
    if task.status == AnalysisTaskStatus.COMPLETED and not effective_error:
        return ["workspace", "report"]
    if task.status in (AnalysisTaskStatus.FAILED,) or effective_error:
        policy = recovery_policy_for(effective_error)
        if policy == "resubmit" and task.pipeline_type == "annotation_kinematics":
            return ["resubmit", "details"]
        if policy == "retry":
            return ["retry", "details"]
        return ["details"]
    return ["details"]


def _resolve_pipeline_type(payload: AnalysisSubmit) -> tuple[str, str]:
    """按 design §4 规则解析 pipeline_type / pipeline_version。"""
    from app.schemas.analysis import (
        ANNOTATION_PIPELINE_VERSION,
        MODEL_PIPELINE_VERSION,
        SUPPORTED_PIPELINE_VERSIONS,
    )

    if payload.pipeline_type == "hybrid":
        raise ValueError("PIPELINE_NOT_IMPLEMENTED:hybrid 尚未实现")

    if payload.pipeline_type:
        ptype = payload.pipeline_type
    elif payload.normalized_annotation_id:
        ptype = "annotation_kinematics"
    else:
        ptype = "model_service"

    if ptype == "annotation_kinematics" and payload.normalized_annotation_id is None:
        raise ValueError("annotation_kinematics 必须提供 normalized_annotation_id")

    if payload.pipeline_version:
        pversion = payload.pipeline_version
    elif ptype == "annotation_kinematics":
        pversion = ANNOTATION_PIPELINE_VERSION
    else:
        pversion = MODEL_PIPELINE_VERSION

    if pversion not in SUPPORTED_PIPELINE_VERSIONS.get(ptype, set()):
        raise ValueError(f"UNSUPPORTED_PIPELINE_VERSION:{ptype}+{pversion}")

    return ptype, pversion


def create_analysis_task(db: Session, payload: AnalysisSubmit) -> AnalysisTask:
    # 锁定 TrainingSession 行，避免并发提交穿透活跃任务检查（design Decision 17）
    session = db.scalar(
        select(TrainingSession)
        .where(TrainingSession.id == payload.session_id)
        .with_for_update()
    )
    if not session:
        raise ValueError("训练记录不存在")

    # ── 活跃任务防重（仅限制 annotation_kinematics）──
    if payload.pipeline_type in (None, "annotation_kinematics") or _resolve_pipeline_type(payload)[0] == "annotation_kinematics":
        active = db.scalar(
            select(AnalysisTask)
            .where(
                AnalysisTask.session_id == payload.session_id,
                AnalysisTask.pipeline_type == "annotation_kinematics",
                AnalysisTask.status.in_([
                    AnalysisTaskStatus.QUEUED,
                    AnalysisTaskStatus.PROCESSING,
                    AnalysisTaskStatus.RESULT_SAVING,
                ]),
            )
            .with_for_update()
        )
        if active:
            raise AnalysisTaskAlreadyActiveError(active.id)

    # ── resolve pipeline type / version ──
    pipeline_type, pipeline_version = _resolve_pipeline_type(payload)

    # ── resolve annotation ──
    annotation: NormalizedAnnotation | None = None
    if payload.normalized_annotation_id:
        annotation = db.get(NormalizedAnnotation, payload.normalized_annotation_id)
        if not annotation or annotation.session_video.session_id != payload.session_id:
            raise ValueError("指定的标准化标注不存在或不属于当前训练记录")
    elif pipeline_type == "annotation_kinematics":
        # annotation_kinematics 必须有 annotation
        raise ValueError("annotation_kinematics 必须提供 normalized_annotation_id")
    else:
        all_side = db.scalars(
            select(NormalizedAnnotation)
            .join(SessionVideo)
            .where(
                SessionVideo.session_id == payload.session_id,
                SessionVideo.view_type == ViewType.SIDE,
            )
        ).all()

        submittable = [
            na for na in all_side
            if na.annotation_file
            and na.annotation_file.status.value == "parsed"
            and na.quality
            and na.quality.get("status") in ("valid", "warning")
        ]

        if submittable:
            raise AnnotationSelectionRequiredError(
                candidate_ids=[na.id for na in submittable]
            )

        if all_side:
            raise AnnotationInputUnavailableError(
                reason="NO_SUBMITTABLE_ANNOTATION"
            )

        annotation = None

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
        pipeline_type=pipeline_type,
        pipeline_version=pipeline_version,
        execution_state={
            "schema_version": "analysis-execution.v1",
            "pipeline": {"type": pipeline_type, "version": pipeline_version},
            "steps": {},
            "warnings": [],
        },
    )
    db.add(task)
    db.flush()
    request_payload["task_id"] = task.id
    session_video_id = annotation.session_video_id if annotation and annotation.session_video_id else None
    video_file_id = (
        annotation.session_video.video_file_id
        if annotation and annotation.session_video
        else None
    )
    request_payload["analysis_input"] = {
        "type": "normalized_annotation",
        "annotation_id": annotation.id if annotation else None,
        "annotation_revision": annotation.revision if annotation else None,
        "session_video_id": session_video_id,
        "video_file_id": video_file_id,
        "annotation_quality_snapshot": quality_snapshot,
        "quality_warning_acknowledged": payload.acknowledge_quality_warnings,
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

        from app.services.analysis_pipelines.registry import resolve

        pipeline = resolve(task.pipeline_type)
        await pipeline.run(task.id, task.pipeline_version)
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


def retry_analysis_task(db: Session, task: AnalysisTask) -> AnalysisTask:
    """仅 annotation_kinematics 失败任务可重试（design §17）。"""
    if task.pipeline_type != "annotation_kinematics":
        raise ValueError("RETRY_NOT_SUPPORTED: 仅 annotation_kinematics 支持重试")
    if task.status != AnalysisTaskStatus.FAILED:
        raise ValueError("RETRY_ONLY_FAILED: 仅失败任务可重试")

    # 保留 previous failure 到 execution_state
    state = dict(task.execution_state or {})
    state["previous_failure"] = {
        "stage": task.failed_stage,
        "code": task.error_code,
        "message": task.error_message,
    }
    task.execution_state = state
    task.status = AnalysisTaskStatus.QUEUED
    task.stage = "queued"
    task.progress = 5
    task.error_code = None
    task.error_message = None
    task.failed_stage = None
    if task.session:
        task.session.status = TrainingSessionStatus.ANALYZING
        db.add(task.session)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


# ── 流水线进度统一投影（design Decision 18/19/24）──

# annotation_kinematics 规范有序阶段（与 checkpoints.STAGE_PROGRESS 对齐）
ANNOTATION_KINEMATICS_STAGE_ORDER = [
    "validating_input",
    "calculating_metrics",
    "generating_artifacts",
    "running_findings",
    "saving_result",
    "assembling_report",
    "completed",
]

# model_service 规范阶段（与 model_service pipeline 实际 stage 对齐）
MODEL_SERVICE_STAGE_ORDER = [
    "model_inference",
    "completed",
]

PIPELINE_STAGE_SPECS: dict[str, list[str]] = {
    "annotation_kinematics": ANNOTATION_KINEMATICS_STAGE_ORDER,
    "model_service": MODEL_SERVICE_STAGE_ORDER,
}

# 规范阶段对应的展示进度百分比（未知阶段默认 0）
_STAGE_PROGRESS = {
    "validating_input": 10,
    "calculating_metrics": 25,
    "generating_artifacts": 45,
    "running_findings": 65,
    "saving_result": 78,
    "assembling_report": 88,
    "completed": 100,
    "model_inference": 50,
}


def build_pipeline_progress(task: AnalysisTask) -> "PipelineProgressRead":
    """将任务投影为前端使用的有序流水线进度（design Decision 18）。"""
    from app.schemas.analysis import PipelineProgressRead, PipelineStepRead

    stage_order = PIPELINE_STAGE_SPECS.get(task.pipeline_type)
    state = task.execution_state or {}
    persisted_steps: dict = state.get("steps", {}) or {}
    warnings: list = state.get("warnings", []) or []

    progress = PipelineProgressRead(
        pipeline_type=task.pipeline_type,
        pipeline_version=task.pipeline_version,
        attempt_count=task.attempt_count or 0,
        current_stage=task.stage,
        failed_stage=task.failed_stage,
        error_code=task.error_code,
        warnings=warnings,
        steps=[],
    )

    # 未命中规范（legacy / 未知 pipeline）：仅返回原始 stage 作为单个 step
    if not stage_order:
        progress.steps = [
            PipelineStepRead(
                key=task.stage,
                status=_step_status_for(task),
                progress=_STAGE_PROGRESS.get(task.stage, 0),
                error_code=task.error_code if task.status == AnalysisTaskStatus.FAILED else None,
                error_message=task.error_message if task.status == AnalysisTaskStatus.FAILED else None,
            )
        ]
        return progress

    current_idx = stage_order.index(task.stage) if task.stage in stage_order else len(stage_order)
    failed_idx = (
        stage_order.index(task.failed_stage)
        if task.failed_stage in stage_order
        else -1
    )

    for idx, key in enumerate(stage_order):
        # 优先使用持久化的真实状态
        if key in persisted_steps:
            ps = persisted_steps[key]
            status = ps.get("status", "completed") if isinstance(ps, dict) else "completed"
            progress.steps.append(
                PipelineStepRead(
                    key=key,
                    status=status,
                    progress=_STAGE_PROGRESS.get(key, 0),
                    details=ps.get("details", {}) if isinstance(ps, dict) else {},
                    error_code=ps.get("error_code") if isinstance(ps, dict) else None,
                    error_message=ps.get("error_message") if isinstance(ps, dict) else None,
                )
            )
            continue

        # 否则按 task 整体状态推导
        if task.status == AnalysisTaskStatus.COMPLETED:
            status = "completed"
        elif task.status == AnalysisTaskStatus.FAILED:
            if failed_idx == -1:
                status = "pending"
            elif idx < failed_idx:
                status = "completed"
            elif idx == failed_idx:
                status = "failed"
            else:
                status = "pending"
        elif task.status == AnalysisTaskStatus.PROCESSING:
            if idx < current_idx:
                status = "completed"
            elif idx == current_idx:
                status = "running"
            else:
                status = "pending"
        else:
            status = "pending"

        progress.steps.append(
            PipelineStepRead(
                key=key,
                status=status,
                progress=_STAGE_PROGRESS.get(key, 0),
                error_code=task.error_code if status == "failed" else None,
                error_message=task.error_message if status == "failed" else None,
            )
        )

    return progress


def _step_status_for(task: AnalysisTask) -> str:
    if task.status == AnalysisTaskStatus.COMPLETED:
        return "completed"
    if task.status == AnalysisTaskStatus.FAILED:
        return "failed"
    if task.status == AnalysisTaskStatus.PROCESSING:
        return "running"
    return "pending"


def _report_exists_for_task(db, task: AnalysisTask) -> bool:
    """判断是否存在指向该任务的报告实体（design Decision 20/21）。"""
    if db is None:
        return True
    return db.scalar(
        select(ReportMetadata.id).where(ReportMetadata.task_id == task.id).limit(1)
    ) is not None


def build_analysis_common_payload(task: AnalysisTask, db=None) -> dict:
    """列表/详情/status 三条路由共享的字段（design Decision 24）。

    对于 annotation_kinematics 流水线，任务 completed 但缺少报告实体时，
    合成 REPORT_METADATA_MISSING 失败（design Decision 20/21）：前端据此复用
    analysis_failed 的失败恢复 UI，而非错误地展示报告可用。
    """
    failed_stage = task.failed_stage
    error_code = task.error_code

    if (
        task.status == AnalysisTaskStatus.COMPLETED
        and task.pipeline_type == "annotation_kinematics"
        and not _report_exists_for_task(db, task)
    ):
        failed_stage = failed_stage or "assembling_report"
        error_code = error_code or "REPORT_METADATA_MISSING"

    return {
        "pipeline_type": task.pipeline_type,
        "pipeline_version": task.pipeline_version,
        "attempt_count": task.attempt_count or 0,
        "failed_stage": failed_stage,
        "error_code": error_code,
        "pipeline_progress": build_pipeline_progress(task),
        "actions": task_actions(task, error_code),
    }


def read_analysis_task(task: AnalysisTask, db=None) -> "AnalysisTaskRead":
    from app.schemas.analysis import AnalysisTaskRead

    data = {
        "id": task.id,
        "session_id": task.session_id,
        "status": task.status,
        "progress": task.progress,
        "stage": task.stage,
        "request_payload": task.request_payload or {},
        "error_message": task.error_message,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "completed_at": task.completed_at,
    }
    data.update(build_analysis_common_payload(task, db))
    return AnalysisTaskRead(**data)


def read_analysis_status(task: AnalysisTask, db=None) -> "AnalysisStatusRead":
    from app.schemas.analysis import AnalysisStatusRead

    data = {
        "task_id": task.id,
        "session_id": task.session_id,
        "status": task.status,
        "progress": task.progress,
        "stage": task.stage,
        "error_message": task.error_message,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "completed_at": task.completed_at,
    }
    data.update(build_analysis_common_payload(task, db))
    return AnalysisStatusRead(**data)
