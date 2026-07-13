"""side-view metrics 服务层：编排计算 + 持久化到 annotation_metrics。

与 analysis_service 解耦：不接入 ModelServiceClient，不写 analysis_results。
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AnnotationMetric, NormalizedAnnotation
from app.services.metrics.engine import calculate_side_view_metrics


def _annotation_to_dict(ann: NormalizedAnnotation) -> dict:
    """把 ORM 对象转成引擎消费的 dict（与 fixture/JSON 同构）。"""
    return {
        "fps": float(ann.fps) if ann.fps else 0,
        "scale": ann.scale or {},
        "events": ann.events or [],
        "keypoint_frames": ann.keypoint_frames or [],
        "reference_lines": ann.reference_lines,
        "distance_markers": ann.distance_markers,
        "swim_direction": ann.swim_direction,
    }


def calculate_and_persist(
    db: Session,
    normalized_annotation_id: int,
    *,
    persist: bool = False,
    current_user_id: int | None = None,
) -> tuple[dict, int | None]:
    """计算 side-view metrics。

    :return: (metrics_dict, annotation_metric_id) ；persist=False 时 id 为 None
    """
    ann = db.scalar(
        select(NormalizedAnnotation)
        .where(NormalizedAnnotation.id == normalized_annotation_id)
    )
    if not ann:
        raise ValueError(f"标准化标注 {normalized_annotation_id} 不存在")

    view_type = ann.session_video.view_type.value if ann.session_video else "side"
    if view_type != "side":
        raise ValueError(f"camera_view={view_type} 不是 side，本引擎仅支持侧面视角")

    ann_dict = _annotation_to_dict(ann)
    metrics = calculate_side_view_metrics(ann_dict, view_type)

    if not persist:
        return metrics, None

    # upsert：同一 (normalized_annotation_id, calculator, calculator_version) 唯一
    existing = db.scalar(
        select(AnnotationMetric).where(
            AnnotationMetric.normalized_annotation_id == normalized_annotation_id,
            AnnotationMetric.calculator == metrics.get("calculator", "side_view_metrics"),
            AnnotationMetric.calculator_version == metrics.get("calculator_version", "0.1.0"),
        )
    )
    if existing:
        existing.metrics = metrics
        existing.quality = metrics.get("quality", {})
        existing.camera_view = view_type
        existing.session_video_id = ann.session_video_id
        record = existing
    else:
        record = AnnotationMetric(
            normalized_annotation_id=normalized_annotation_id,
            session_video_id=ann.session_video_id,
            camera_view=view_type,
            metrics=metrics,
            quality=metrics.get("quality", {}),
            calculator=metrics.get("calculator", "side_view_metrics"),
            calculator_version=metrics.get("calculator_version", "0.1.0"),
            created_by=current_user_id,
        )
        db.add(record)
    db.commit()
    db.refresh(record)
    return metrics, record.id


def get_latest_metric(db: Session, normalized_annotation_id: int) -> AnnotationMetric | None:
    return db.scalar(
        select(AnnotationMetric)
        .where(AnnotationMetric.normalized_annotation_id == normalized_annotation_id)
        .order_by(AnnotationMetric.created_at.desc())
    )


def get_metric_by_id(db: Session, annotation_metric_id: int) -> AnnotationMetric | None:
    return db.scalar(
        select(AnnotationMetric).where(AnnotationMetric.id == annotation_metric_id)
    )
