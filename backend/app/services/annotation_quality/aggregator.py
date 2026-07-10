"""AnalysisQualityAggregator — 两阶段质量聚合。"""

from app.services.annotation_quality.models import (
    AnalysisQualitySummary,
    AnnotationQualityReport,
    MetricQualityReport,
    ModuleAvailability,
    QualityDecision,
    QualityStatus,
)

AVAILABILITY_ORDER = {"ready": 0, "degraded": 1, "blocked": 2}


def combine_availability(annotation_status: str, metric_status: str) -> str:
    if annotation_status == "blocked":
        return "blocked"
    if metric_status in ("failed", "unavailable"):
        return "blocked"
    if annotation_status == "degraded":
        return "degraded"
    if metric_status in ("warning", "low_confidence", "partial"):
        return "degraded"
    return "ready"


MODULE_METRIC_KEY_MAP: dict[str, list[str]] = {
    "body_position": ["body_angle_deg_avg", "hip_depth_cm_avg", "streamline_index"],
    "arm_entry": ["entry_angle_deg_avg", "front_reach_distance_cm_avg", "elbow_angle_deg_avg", "forearm_drop_angle_deg_avg"],
    "catch_pull": ["elbow_angle_deg_avg", "forearm_drop_angle_deg_avg"],
    "leg_kick": ["knee_angle_deg_avg", "hip_angle_deg_avg", "ankle_extension_angle_deg_avg", "kick_frequency_hz"],
    "efficiency": ["stroke_rate_spm_avg", "stroke_length_m_avg", "average_speed_mps", "swolf"],
}


class AnalysisQualityAggregator:
    def aggregate(
        self,
        annotation_quality: AnnotationQualityReport,
        metric_quality: MetricQualityReport | None,
    ) -> AnalysisQualitySummary:
        annotation_dict = annotation_quality.model_dump(mode="json")
        metrics_dict = metric_quality.model_dump(mode="json") if metric_quality else {}

        module_avail = ModuleAvailability()

        for module_key in ("body_position", "arm_entry", "catch_pull", "leg_kick", "efficiency"):
            annot_readiness = annotation_quality.module_readiness.get(module_key)
            annot_status = annot_readiness.status if annot_readiness else "ready"
            if metric_quality:
                metric_keys = MODULE_METRIC_KEY_MAP.get(module_key, [])
                metric_avail = min(
                    (metric_quality.metric_availability.get(k, "unavailable") for k in metric_keys),
                    key=lambda v: AVAILABILITY_ORDER.get(v, 3),
                ) if metric_keys else "available"
            else:
                metric_avail = "available"

            combined = combine_availability(annot_status, metric_avail)
            setattr(module_avail, module_key, combined)

        all_blocked = all(
            getattr(module_avail, mk) == "blocked"
            for mk in ("body_position", "arm_entry", "catch_pull")
        )
        if annotation_quality.status == "invalid" or all_blocked:
            analysis_allowed = False
            report_avail = "blocked"
        elif any(
            getattr(module_avail, mk) in ("degraded", "blocked")
            for mk in ("body_position", "arm_entry", "catch_pull", "leg_kick", "efficiency")
        ):
            analysis_allowed = True
            report_avail = "degraded"
        else:
            analysis_allowed = True
            report_avail = "full"

        return AnalysisQualitySummary(
            schema_version="analysis-quality.v1",
            annotation=annotation_dict,
            metrics=metrics_dict,
            decision=QualityDecision(
                analysis_allowed=analysis_allowed,
                report_availability=report_avail,
                module_availability=module_avail,
            ),
        )
