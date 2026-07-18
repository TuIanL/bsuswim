"""Overview statistics for page 1 — NOT part of the canonical metric registry."""

from app.schemas.kinematics_report import (
    ReportMetric,
    ReportOverviewStat,
    ReportOverviewStatSource,
)


def _count_available(index: dict[str, ReportMetric]) -> int:
    return sum(1 for m in index.values() if m.availability == "available")


def _count_low_confidence(index: dict[str, ReportMetric]) -> int:
    return sum(1 for m in index.values() if m.availability == "low_confidence")


def _count_available_modules(index: dict[str, ReportMetric]) -> dict[str, int]:
    """Count metrics per category with at least one available or low_confidence metric."""
    modules: dict[str, int] = {}
    for m in index.values():
        if m.availability in ("available", "low_confidence"):
            modules[m.category] = modules.get(m.category, 0) + 1
    return modules


def build_overview_stats(
    annotation: object,         # NormalizedAnnotation
    metric_quality: dict,
    all_report_metrics: dict[str, ReportMetric],
    effective_frame_count: int,
) -> list[ReportOverviewStat]:
    """Build overview statistics for page 1.

    effective_frame_count can come from len(annotation.effective_keypoint_frames)
    or similar — call site provides it to avoid coupling.
    """
    keypoint_frames = getattr(annotation, "keypoint_frames", None)
    total_frames = len(keypoint_frames) if isinstance(keypoint_frames, list) else 0

    available_count = _count_available(all_report_metrics)
    low_conf_count = _count_low_confidence(all_report_metrics)
    total_metrics = len(all_report_metrics)
    non_unavailable = available_count + low_conf_count
    available_ratio = non_unavailable / total_metrics if total_metrics > 0 else 0.0

    modules = _count_available_modules(all_report_metrics)
    available_module_count = len(modules)

    joint_schema = getattr(annotation, "joint_schema", None)

    stats: list[ReportOverviewStat] = [
        ReportOverviewStat(
            key="effective_frame_count",
            label="有效标注帧数",
            value=effective_frame_count,
            source=ReportOverviewStatSource.NORMALIZED_ANNOTATION,
        ),
        ReportOverviewStat(
            key="total_frame_count",
            label="原始标注帧数",
            value=total_frames,
            source=ReportOverviewStatSource.NORMALIZED_ANNOTATION,
        ),
        ReportOverviewStat(
            key="joint_schema",
            label="关节点骨架",
            value=joint_schema,
            display_value=str(joint_schema) if joint_schema else None,
            source=ReportOverviewStatSource.NORMALIZED_ANNOTATION,
        ),
        ReportOverviewStat(
            key="total_metrics",
            label="总指标数",
            value=total_metrics,
            source=ReportOverviewStatSource.REPORT_ASSEMBLY,
        ),
        ReportOverviewStat(
            key="available_metric_count",
            label="可用指标数",
            value=non_unavailable,
            display_value=f"{non_unavailable}/{total_metrics} ({available_ratio:.1%})",
            source=ReportOverviewStatSource.REPORT_ASSEMBLY,
        ),
        ReportOverviewStat(
            key="low_confidence_metric_count",
            label="低置信度指标数",
            value=low_conf_count,
            source=ReportOverviewStatSource.REPORT_ASSEMBLY,
        ),
        ReportOverviewStat(
            key="available_module_count",
            label="可用模块数",
            value=available_module_count,
            display_value=str(available_module_count),
            source=ReportOverviewStatSource.REPORT_ASSEMBLY,
        ),
    ]
    return stats
