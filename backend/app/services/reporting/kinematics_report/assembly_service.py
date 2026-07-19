"""Database-backed assembly service for five-page kinematics reports."""

from fastapi import HTTPException, status

from sqlalchemy.orm import Session

from app.models import AnnotationMetric, NormalizedAnnotation, User
from app.models.athlete import Athlete
from app.models.training_session import TrainingSession
from app.models.video import SessionVideo, VideoFile
from app.schemas.kinematics_report import (
    ArtifactResolutionResult,
    FivePageKinematicsReport,
    FivePageReportAssemblyContext,
)
from app.services.diagnostics.review_findings.generation_service import get_current_review_findings
from app.services.kinematic_artifacts.resolver import resolve_current_artifact_set


ASSEMBLY_REQUIRED_CALCULATOR = "side_2d_kinematics"
ASSEMBLY_REQUIRED_SCHEMA = "swim-side-kinematics.v1"


class AssemblyError(HTTPException):
    def __init__(self, detail: str, code: str, http_status: int = status.HTTP_422_UNPROCESSABLE_ENTITY):
        super().__init__(status_code=http_status, detail={"detail": detail, "code": code})


def _validate_metric(metric: AnnotationMetric, annotation: NormalizedAnnotation) -> None:
    if metric.calculator != ASSEMBLY_REQUIRED_CALCULATOR:
        raise AssemblyError(
            "不支持的 calculator，需要 side_2d_kinematics",
            "unsupported_metric_schema",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    if metric.schema_version != ASSEMBLY_REQUIRED_SCHEMA:
        raise AssemblyError(
            f"不支持的 schema，需要 {ASSEMBLY_REQUIRED_SCHEMA}",
            "unsupported_metric_schema",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    if not isinstance(metric.metrics, dict) or "summary" not in metric.metrics:
        raise AssemblyError(
            "metrics 顶层结构损坏（缺少 summary）",
            "invalid_metric_payload",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    if metric.source_revision is not None and metric.source_revision != annotation.revision:
        raise AssemblyError(
            f"metric source_revision {metric.source_revision} 与标注 revision {annotation.revision} 不一致",
            "metric_revision_stale",
            status.HTTP_409_CONFLICT,
        )


def _resolve_ownership(
    db: Session,
    metric: AnnotationMetric,
    current_user: User,
) -> NormalizedAnnotation:
    """Validate ownership: annotation → session_video → session → coach_id."""
    ann = db.get(NormalizedAnnotation, metric.normalized_annotation_id)
    if ann is None:
        raise AssemblyError("关联标注不存在", "annotation_unavailable", status.HTTP_404_NOT_FOUND)
    sv = db.get(SessionVideo, metric.session_video_id) if metric.session_video_id else None
    if sv is not None:
        session = db.get(TrainingSession, sv.session_id)
    else:
        session = None
    if session is None or session.coach_id != current_user.id:
        raise AssemblyError("无权限访问该指标", "metric_unavailable", status.HTTP_404_NOT_FOUND)
    return ann


def assemble_five_page_kinematics_report(
    db: Session,
    annotation_metric_id: int,
    current_user: User,
) -> FivePageKinematicsReport:
    """Resolve all inputs, validate, and assemble the five-page report.

    This service does NOT persist ReportMetadata (reserved for Change 7).
    """
    # 1. Resolve AnnotationMetric
    metric = db.get(AnnotationMetric, annotation_metric_id)
    if metric is None:
        raise AssemblyError("annotation_metrics 不存在", "metric_unavailable", status.HTTP_404_NOT_FOUND)

    # 2. Ownership + resolve NormalizedAnnotation
    annotation = _resolve_ownership(db, metric, current_user)

    # 3. Validate schema/revision
    _validate_metric(metric, annotation)

    # 4. Resolve upstream entities
    session_video = db.get(SessionVideo, metric.session_video_id) if metric.session_video_id else None
    video_file = None
    session = None
    athlete = None
    if session_video is not None:
        video_file = db.get(VideoFile, session_video.video_file_id)
        session = db.get(TrainingSession, session_video.session_id)
        if session is not None:
            athlete = db.get(Athlete, session.athlete_id)

    # 5. Resolve artifact set (via current resolver)
    artifact_result: ArtifactResolutionResult = resolve_current_artifact_set(
        db, metric, annotation, video_file
    )

    # 6. Resolve review finding set (via existing resolver)
    # 仅 review_findings_not_generated 允许降级为 partial 报告；
    # invalid_rule_set / rule_output_kind_mismatch / metric_revision_stale 等结构性
    # 错误必须正常向上抛出，不得静默降级（design §12.2-12.4）。
    from app.services.diagnostics.review_findings.generation_service import (
        ReviewFindingsGenerationError,
    )

    finding_set = None
    try:
        finding_set = get_current_review_findings(db, annotation_metric_id, current_user)
    except ReviewFindingsGenerationError as exc:
        if exc.code != "review_findings_not_generated":
            raise
        finding_set = None

    # 7. Assemble
    ctx = FivePageReportAssemblyContext(
        annotation_metric=metric,
        normalized_annotation=annotation,
        athlete=athlete,
        session=session,
        video_file=video_file,
        session_video=session_video,
        artifact_set=artifact_result.artifact_set,
        finding_set=finding_set,
        artifact_resolution=artifact_result,
    )

    from .assembler import build_five_page_kinematics_report
    report = build_five_page_kinematics_report(ctx)

    # 8. Fill in context
    report.context = _build_report_context(ctx)

    return report


def _build_report_context(ctx: FivePageReportAssemblyContext):
    """Build the report context block from assembly context."""
    from .page_builders import (
        _build_athlete_context,
        _build_session_context,
        _build_video_context,
        _build_annotation_context,
    )
    return {
        "athlete": _build_athlete_context(ctx),
        "session": _build_session_context(ctx),
        "video": _build_video_context(ctx),
        "annotation": _build_annotation_context(ctx),
        "analysis_scope": {},
    }
