"""side_2d_kinematics 质量聚合适配器（专用，不扩展旧 AnalysisQualityAggregator）。

把 Side2DKinematicsQualityEvaluator 的 issue 列表与 annotation 质量快照，
桥接成 four-page 报告使用的 4 模块 availability（body_posture / upper_limb /
lower_limb / head_trunk），并产出 analysis-quality.v1 的 AnalysisQualitySummary。
"""
from __future__ import annotations

from typing import Any

from app.services.annotation_quality.models import (
    AnalysisQualitySummary,
    AnnotationQualityReport,
    MetricQualityReport,
    ModuleAvailability,
    QualityDecision,
)

# evaluator issue code → 受影响的报告模块
ISSUE_MODULE_MAP: dict[str, list[str]] = {
    "REFERENCE_BODY_LENGTH_INSUFFICIENT": ["body_posture", "upper_limb", "lower_limb"],
    "TEMPORAL_CONTINUITY_LOW": ["body_posture"],
    "FRAME_MAPPING_UNVERIFIED": ["body_posture"],
    "HEAD_POINTS_INSUFFICIENT": ["head_trunk"],
    "STROKE_CONTEXT_UNKNOWN": ["upper_limb", "lower_limb"],
    "METRIC_SAMPLE_INSUFFICIENT": ["body_posture", "upper_limb", "lower_limb", "head_trunk"],
    "SINGLE_SIDE_FALLBACK": ["upper_limb", "lower_limb"],
    "PERIODICITY_PEAK_WEAK": ["lower_limb"],
}

# annotation 5 模块 → 报告 4 模块
ANNOTATION_MODULE_TO_REPORT: dict[str, str] = {
    "body_position": "body_posture",
    "arm_entry": "upper_limb",
    "catch_pull": "upper_limb",
    "leg_kick": "lower_limb",
    "efficiency": "lower_limb",
}

REPORT_MODULES = ["body_posture", "upper_limb", "lower_limb", "head_trunk"]

_AVAIL_ORDER = {"ready": 0, "degraded": 1, "blocked": 2}


def _worse(a: str, b: str) -> str:
    return a if _AVAIL_ORDER.get(a, 3) >= _AVAIL_ORDER.get(b, 3) else b


def _combine(annotation_status: str, metric_status: str) -> str:
    if annotation_status == "blocked":
        return "blocked"
    if metric_status in ("failed", "unavailable"):
        return "blocked"
    if annotation_status == "degraded":
        return "degraded"
    if metric_status in ("warning", "low_confidence", "partial", "degraded"):
        return "degraded"
    return "ready"


def aggregate_side_2d_kinematics_quality(
    annotation_quality: AnnotationQualityReport | dict | None,
    metric_quality: dict | MetricQualityReport | None,
) -> AnalysisQualitySummary:
    """桥接 annotation 质量与 side_2d_kinematics metric 质量到 4 报告模块。"""
    ann = (
        annotation_quality
        if isinstance(annotation_quality, AnnotationQualityReport)
        else AnnotationQualityReport.model_validate(annotation_quality or {})
    )
    metric_dict = (
        metric_quality.model_dump(mode="json")
        if isinstance(metric_quality, MetricQualityReport)
        else (metric_quality or {})
    )

    issues: list[dict] = metric_dict.get("issues", []) or []

    # 1) 从 evaluator issues 推导每个报告模块的 metric 侧可用性
    module_metric_avail: dict[str, str] = {m: "ready" for m in REPORT_MODULES}
    for issue in issues:
        code = issue.get("code")
        affected = ISSUE_MODULE_MAP.get(code, [])
        for mod in affected:
            module_metric_avail[mod] = _worse(module_metric_avail[mod], "degraded")

    # 2) 从 annotation 5 模块 readiness 桥接
    module_annotation_avail: dict[str, str] = {m: "ready" for m in REPORT_MODULES}
    for ann_module, readiness in (ann.module_readiness or {}).items():
        report_mod = ANNOTATION_MODULE_TO_REPORT.get(ann_module, "body_posture")
        a_status = readiness.status if readiness else "ready"
        module_annotation_avail[report_mod] = _worse(
            module_annotation_avail[report_mod], a_status
        )

    # 3) 合并
    module_availability: dict[str, str] = {}
    for mod in REPORT_MODULES:
        module_availability[mod] = _combine(
            module_annotation_avail[mod], module_metric_avail[mod]
        )

    # 4) 整体决策
    if any(v == "blocked" for v in module_availability.values()):
        report_availability: str = "blocked"
    elif any(v == "degraded" for v in module_availability.values()):
        report_availability = "degraded"
    else:
        report_availability = "full"

    def _mlist() -> list[str]:
        return [m for m, v in module_availability.items() if v != "ready"]

    # 把 4 报告模块 availability 抬升回 5-key ModuleAvailability：
    # body_posture→body_position；upper_limb→arm_entry+catch_pull；
    # lower_limb→leg_kick+efficiency；head_trunk→（无对应 5-key，并入 body_position）
    module_avail = ModuleAvailability(
        body_position=module_availability["body_posture"],
        arm_entry=module_availability["upper_limb"],
        catch_pull=module_availability["upper_limb"],
        leg_kick=module_availability["lower_limb"],
        efficiency=module_availability["lower_limb"],
    )

    decision = QualityDecision(
        analysis_allowed=report_availability != "blocked",
        report_availability=report_availability,  # type: ignore[arg-type]
        module_availability=module_avail,
    )

    metrics_out = dict(metric_dict)
    metrics_out["side_2d_kinematics_module_availability"] = module_availability

    return AnalysisQualitySummary(
        annotation=ann.model_dump(mode="json"),
        metrics=metrics_out,
        decision=decision,
    )
