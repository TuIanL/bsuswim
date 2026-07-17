"""side-view metrics 服务层：编排计算 + 持久化到 annotation_metrics。

与 analysis_service 解耦：不接入 ModelServiceClient，不写 analysis_results。

v2 扩展：支持通过 ``calculator`` 名字从注册表选择计算器；UPSERT 刷新
``source_revision`` / ``schema_version`` / ``metrics`` / ``quality`` /
``updated_at``；读取按 calculator 过滤并按 ``updated_at`` DESC 排序。
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AnnotationMetric, NormalizedAnnotation
from app.services.metrics.kinematics.protocols import MetricCalculationContext
from app.services.metrics.kinematics.registry import (
    get_calculator,
    has_calculator,
    register_builtin_calculators,
)
from app.schemas.metrics import CALCULATOR_SIDE_VIEW_METRICS


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


def _resolve_stroke_type(ann: NormalizedAnnotation) -> str | None:
    meta = ann.annotation_metadata or {}
    if isinstance(meta, dict) and meta.get("stroke_type"):
        return meta["stroke_type"]
    return None


def calculate_and_persist(
    db: Session,
    normalized_annotation_id: int,
    *,
    persist: bool = False,
    current_user_id: int | None = None,
    calculator: str = CALCULATOR_SIDE_VIEW_METRICS,
) -> tuple[dict, int | None]:
    """计算指定 calculator 的 metrics。

    :param calculator: 注册表里的计算器名字（默认 side_view_metrics）。
    :return: (metrics_dict, annotation_metric_id) ；persist=False 时 id 为 None
    """
    register_builtin_calculators()

    ann = db.scalar(
        select(NormalizedAnnotation)
        .where(NormalizedAnnotation.id == normalized_annotation_id)
    )
    if not ann:
        raise ValueError(f"标准化标注 {normalized_annotation_id} 不存在")

    view_type = ann.session_video.view_type.value if ann.session_video else "side"
    if view_type != "side":
        raise ValueError(f"camera_view={view_type} 不是 side，本引擎仅支持侧面视角")

    keypoint_frames = ann.keypoint_frames or []
    if not keypoint_frames:
        raise ValueError("no usable skeleton frames: keypoint_frames 为空")

    if not has_calculator(calculator):
        raise ValueError(f"unsupported calculator: {calculator}")

    calc = get_calculator(calculator)
    ann_dict = _annotation_to_dict(ann)
    context = MetricCalculationContext(
        normalized_annotation_id=normalized_annotation_id,
        source_revision=int(ann.revision),
        camera_view=view_type,
        annotation_metadata=ann.annotation_metadata or {},
        stroke_type=_resolve_stroke_type(ann),
    )
    metrics = calc.calculate(ann_dict, context)

    # 确保顶层携带计算器元信息，供持久化使用
    metrics.setdefault("calculator", calc.name)
    metrics.setdefault("calculator_version", calc.version)
    metrics.setdefault("schema_version", calc.schema_version)

    if not persist:
        return metrics, None

    # upsert：同一 (normalized_annotation_id, calculator, calculator_version) 唯一
    existing = db.scalar(
        select(AnnotationMetric).where(
            AnnotationMetric.normalized_annotation_id == normalized_annotation_id,
            AnnotationMetric.calculator == metrics.get("calculator", calculator),
            AnnotationMetric.calculator_version == metrics.get("calculator_version", "0.1.0"),
        )
    )
    if existing:
        existing.metrics = metrics
        existing.quality = metrics.get("quality", {})
        existing.camera_view = view_type
        existing.schema_version = metrics.get("schema_version", existing.schema_version)
        existing.source_revision = context.source_revision
        existing.session_video_id = ann.session_video_id
        existing.updated_at = datetime.now(timezone.utc)
        record = existing
    else:
        record = AnnotationMetric(
            normalized_annotation_id=normalized_annotation_id,
            session_video_id=ann.session_video_id,
            camera_view=view_type,
            metrics=metrics,
            quality=metrics.get("quality", {}),
            calculator=metrics.get("calculator", calculator),
            calculator_version=metrics.get("calculator_version", "0.1.0"),
            schema_version=metrics.get("schema_version", "swim-side-metrics.v1"),
            source_revision=context.source_revision,
            created_by=current_user_id,
        )
        db.add(record)
    db.commit()
    db.refresh(record)
    return metrics, record.id


def get_latest_metric(
    db: Session,
    normalized_annotation_id: int,
    calculator: str | None = None,
) -> AnnotationMetric | None:
    """读取某标注的最新一条 annotation_metrics（可按 calculator 过滤）。

    按 ``updated_at`` DESC 排序（task 2.8）。
    """
    stmt = select(AnnotationMetric).where(
        AnnotationMetric.normalized_annotation_id == normalized_annotation_id
    )
    if calculator:
        stmt = stmt.where(AnnotationMetric.calculator == calculator)
    stmt = stmt.order_by(AnnotationMetric.updated_at.desc())
    return db.scalar(stmt)


def get_metric_by_id(db: Session, annotation_metric_id: int) -> AnnotationMetric | None:
    return db.scalar(
        select(AnnotationMetric).where(AnnotationMetric.id == annotation_metric_id)
    )


def compute_revision_status(record: AnnotationMetric, ann: NormalizedAnnotation) -> str:
    """根据存储 source_revision 与标注当前 revision 计算三态（design D5）。"""
    if record.source_revision is None:
        return "unknown"
    if record.source_revision == int(ann.revision):
        return "current"
    return "stale"
