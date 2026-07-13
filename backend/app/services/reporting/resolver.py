from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AnalysisResult, AnnotationMetric, NormalizedAnnotation
from app.models.video import ViewType


def resolve_annotation_metric_for_result(
    db: Session,
    analysis_result: AnalysisResult,
    *,
    schema_version: str = "swim-side-metrics.v1",
    camera_view: str = "side",
) -> AnnotationMetric | None:
    meta = (analysis_result.raw_result or {}).get("diagnostics_meta") or {}
    if meta.get("annotation_metric_id"):
        metric = db.get(AnnotationMetric, meta["annotation_metric_id"])
        if metric and metric.schema_version == schema_version:
            return metric

    task = analysis_result.task
    if not task or not task.session:
        return None
    side_video = next((v for v in task.session.videos if v.view_type == ViewType.SIDE), None)
    if not side_video:
        return None
    norm = db.scalars(
        select(NormalizedAnnotation)
        .where(NormalizedAnnotation.session_video_id == side_video.id)
        .order_by(NormalizedAnnotation.id.desc())
    ).first()
    if not norm:
        return None
    return db.scalars(
        select(AnnotationMetric)
        .where(
            AnnotationMetric.normalized_annotation_id == norm.id,
            AnnotationMetric.schema_version == schema_version,
        )
        .order_by(AnnotationMetric.id.desc())
    ).first()
