"""annotation_kinematics pipeline — side_2d_v1。

编排四个既有服务：calculate_and_persist → kinematic artifacts → review findings
→ AnalysisResult → five-page report → ReportMetadata。使用 checkpoint-aware
state writer，与 model_service 的 legacy helper 完全隔离。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.session import SessionLocal
from app.models import (
    AnalysisResult,
    AnalysisTask,
    AnnotationMetric,
    NormalizedAnnotation,
    ReportMetadata,
    SessionVideo,
    TrainingSession,
    User,
    ViewType,
)
from app.schemas.metrics import CALCULATOR_SIDE_2D_KINEMATICS
from app.services.analysis_pipelines.checkpoints import (
    PipelineTaskStateWriter,
)
from app.services.analysis_pipelines.errors import (
    ERROR_ARTIFACT_GENERATION_FAILED,
    ERROR_REVIEW_FINDINGS_GENERATION_FAILED,
    ERROR_TASK_OWNER_UNAVAILABLE,
    PipelineExecutionError,
)
from app.services.analysis_pipelines.protocols import PipelineOutcome
from app.services.diagnostics.review_findings.generation_service import generate_review_findings
from app.services.kinematic_artifacts.generation_service import generate as generate_artifacts
from app.services.metrics.kinematics.quality_adapter import aggregate_side_2d_kinematics_quality
from app.services.metrics_service import calculate_and_persist
from app.services.reporting.kinematics_report.assembly_service import (
    AssemblyError,
    assemble_five_page_kinematics_report,
)

ANNOTATION_PIPELINE_VERSION = "side_2d_v1"
REPORT_SCHEMA_VERSION = "swim-analysis.annotation-kinematics.v1"
REVIEW_RULE_SET = "side_2d_kinematics_v1"


def _view_is_side(session_video: SessionVideo) -> bool:
    vt = session_video.view_type
    return (vt.value if hasattr(vt, "value") else vt) == ViewType.SIDE


def _build_source_trace(annotation, metric, artifact_set, finding_set, report) -> dict:
    return {
        "pipeline_type": "annotation_kinematics",
        "pipeline_version": ANNOTATION_PIPELINE_VERSION,
        "normalized_annotation_id": annotation.id,
        "annotation_revision": annotation.revision,
        "annotation_metric_id": metric.id,
        "artifact_generation_signature": getattr(artifact_set, "generation_signature", None),
        "finding_generation_signature": getattr(finding_set, "generation_signature", None),
        "report_generation_signature": getattr(report, "generation_signature", None),
    }


def _persist_report_metadata(db: Session, task: AnalysisTask, report_data: dict) -> ReportMetadata:
    """取得 session 行锁后 upsert ReportMetadata（last-successful-write 语义）。"""
    db.scalar(
        select(TrainingSession)
        .where(TrainingSession.id == task.session_id)
        .with_for_update()
    )
    existing = db.scalar(select(ReportMetadata).where(ReportMetadata.session_id == task.session_id))
    if existing:
        existing.task_id = task.id
        existing.source = "annotation_kinematics"
        existing.report_data = report_data
        existing.generated_at = datetime.utcnow()
        if existing.pdf_status and existing.pdf_status != "not_exported":
            existing.pdf_status = "stale"
        report = existing
    else:
        report = ReportMetadata(
            session_id=task.session_id,
            task_id=task.id,
            source="annotation_kinematics",
            report_data=report_data,
        )
    db.add(report)
    db.flush()
    return report


def _run_sync(task_id: int, pipeline_version: str, db: Optional[Session] = None) -> PipelineOutcome:
    own_session = db is None
    if own_session:
        db = SessionLocal()
    task = db.get(AnalysisTask, task_id, options=[joinedload(AnalysisTask.session)])
    if not task:
        if own_session:
            db.close()
        return PipelineOutcome(task_id, "annotation_kinematics", pipeline_version, completed=False)

    writer = PipelineTaskStateWriter(db, task)
    attempt = task.attempt_count
    try:
        writer.claim()

        # ── validating_input ──
        writer.start_step("validating_input")
        ai = (task.request_payload or {}).get("analysis_input", {})
        annotation_id = ai.get("annotation_id")
        locked_revision = ai.get("annotation_revision")
        if annotation_id is None:
            raise PipelineExecutionError("INVALID_INPUT", "annotation_id 缺失", "validating_input")
        annotation = db.get(NormalizedAnnotation, annotation_id)
        if annotation is None:
            raise PipelineExecutionError("ANNOTATION_NOT_FOUND", "标准化标注不存在", "validating_input")
        if annotation.revision != locked_revision:
            raise PipelineExecutionError(
                "ANNOTATION_REVISION_DRIFT",
                f"标注 revision 从 {locked_revision} 变为 {annotation.revision}",
                "validating_input",
            )
        session_video = annotation.session_video
        if session_video is None or session_video.session_id != task.session_id:
            raise PipelineExecutionError("SESSION_MISMATCH", "session 归属不一致", "validating_input")
        if not _view_is_side(session_video):
            raise PipelineExecutionError("UNSUPPORTED_VIEW", "非侧面机位", "validating_input")
        if not (annotation.keypoint_frames or []):
            raise PipelineExecutionError("NO_KEYPOINT_FRAMES", "keypoint_frames 为空", "validating_input")
        if pipeline_version != ANNOTATION_PIPELINE_VERSION:
            raise PipelineExecutionError(
                "UNSUPPORTED_PIPELINE_VERSION",
                f"不支持的 pipeline_version: {pipeline_version}",
                "validating_input",
            )
        owner = db.get(User, task.session.coach_id) if task.session else None
        if owner is None:
            raise PipelineExecutionError(
                ERROR_TASK_OWNER_UNAVAILABLE,
                "分析任务所属用户不存在",
                "validating_input",
            )
        writer.complete_step(
            "validating_input",
            annotation_id=annotation.id,
            annotation_revision=annotation.revision,
        )

        # ── calculating_metrics ──
        writer.start_step("calculating_metrics")
        metrics, annotation_metric_id = calculate_and_persist(
            db,
            normalized_annotation_id=annotation.id,
            persist=True,
            current_user_id=owner.id,
            calculator=CALCULATOR_SIDE_2D_KINEMATICS,
        )
        metric = db.get(AnnotationMetric, annotation_metric_id)
        if metric is None:
            raise PipelineExecutionError("METRIC_PERSIST_FAILED", "指标未持久化", "calculating_metrics")
        if metric.normalized_annotation_id != annotation.id or metric.source_revision != locked_revision:
            raise PipelineExecutionError("METRIC_REVISION_MISMATCH", "指标 revision 不匹配", "calculating_metrics")
        writer.complete_step("calculating_metrics", annotation_metric_id=metric.id, source_revision=metric.source_revision)

        # ── generating_artifacts ──
        writer.start_step("generating_artifacts")
        force_artifacts = attempt > 1
        try:
            artifact_set, _ = generate_artifacts(
                db,
                metric.id,
                force=force_artifacts,
                current_user_id=owner.id,
            )
        except Exception as exc:
            raise PipelineExecutionError(ERROR_ARTIFACT_GENERATION_FAILED, str(exc), "generating_artifacts") from exc
        artifact_status = getattr(artifact_set, "status", "ready")
        if artifact_status in ("failed", "partial"):
            writer.add_warning(f"artifact set {artifact_status}")
        writer.complete_step(
            "generating_artifacts",
            artifact_set_id=artifact_set.id,
            generation_signature=getattr(artifact_set, "generation_signature", None),
            artifact_status=artifact_status,
        )

        # ── running_findings ──
        writer.start_step("running_findings")
        force_findings = attempt > 1
        try:
            finding_set, _ = generate_review_findings(
                db,
                metric.id,
                owner,
                rule_set=REVIEW_RULE_SET,
                force=force_findings,
            )
        except Exception as exc:
            raise PipelineExecutionError(ERROR_REVIEW_FINDINGS_GENERATION_FAILED, str(exc), "running_findings") from exc
        writer.complete_step(
            "running_findings",
            finding_set_id=finding_set.id,
            generation_signature=getattr(finding_set, "generation_signature", None),
        )

        # ── saving_result ──
        writer.start_step("saving_result")
        quality_summary = aggregate_side_2d_kinematics_quality(
            annotation.quality, metric.quality
        ).model_dump(mode="json")
        existing_result = db.scalar(select(AnalysisResult).where(AnalysisResult.task_id == task.id))
        analysis_result = existing_result or AnalysisResult(task_id=task.id)
        analysis_result.schema_version = REPORT_SCHEMA_VERSION
        analysis_result.detections = []
        analysis_result.keypoint_frames = []
        analysis_result.phases = []
        analysis_result.metrics = metric.metrics
        analysis_result.diagnostics = []
        analysis_result.quality_summary = quality_summary
        analysis_result.raw_result = {
            "pipeline": {"type": "annotation_kinematics", "version": ANNOTATION_PIPELINE_VERSION},
            "input": {"normalized_annotation_id": annotation.id, "annotation_revision": annotation.revision},
            "products": {
                "annotation_metric_id": metric.id,
                "artifact_set_id": artifact_set.id,
                "review_finding_set_id": finding_set.id,
            },
            "review_findings": {
                "finding_set_id": finding_set.id,
                "count": len(getattr(finding_set, "findings", []) or []),
            },
        }
        db.add(analysis_result)
        db.flush()
        writer.complete_step("saving_result", analysis_result_id=analysis_result.id)

        # ── assembling_report ──
        writer.start_step("assembling_report")
        try:
            report_model = assemble_five_page_kinematics_report(db, metric.id, owner)
        except AssemblyError as exc:
            raise PipelineExecutionError("REPORT_ASSEMBLY_FAILED", str(exc), "assembling_report") from exc
        report_data = report_model.model_dump(mode="json")
        report_data["source_trace"] = _build_source_trace(annotation, metric, artifact_set, finding_set, report_model)
        report = _persist_report_metadata(db, task, report_data)
        writer.complete_step(
            "assembling_report",
            report_id=report.id,
            generation_signature=report_data["source_trace"]["report_generation_signature"],
        )

        writer.complete_pipeline(report_id=report.id)
        return PipelineOutcome(task_id, "annotation_kinematics", pipeline_version, completed=True, report_id=report.id)
    except PipelineExecutionError as exc:
        db.rollback()
        writer.fail(exc.stage or "validating_input", exc.code, exc.message)
        return PipelineOutcome(task_id, "annotation_kinematics", pipeline_version, completed=False)
    except Exception as exc:
        db.rollback()
        writer.fail("validating_input", "PIPELINE_INTERNAL_ERROR", str(exc))
        return PipelineOutcome(task_id, "annotation_kinematics", pipeline_version, completed=False)
    finally:
        if own_session:
            db.close()


class AnnotationKinematicsPipeline:
    pipeline_type = "annotation_kinematics"
    supported_versions = {ANNOTATION_PIPELINE_VERSION}

    async def run(self, task_id: int, pipeline_version: str) -> PipelineOutcome:
        from fastapi.concurrency import run_in_threadpool

        return await run_in_threadpool(_run_sync, task_id, pipeline_version)
