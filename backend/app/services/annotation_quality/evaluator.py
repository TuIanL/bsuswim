"""MetricQualityEvaluator — 指标计算质量评估。"""

from datetime import datetime, timezone

from app.services.annotation_quality.issue_codes import ELBOW_ANGLE_SAMPLE_LOW
from app.services.annotation_quality.models import (
    MetricQualityReport,
    QualityIssue,
    QualityStatus,
)

CORE_METRIC_KEYS: list[str] = [
    "body_angle_deg_avg",
    "hip_depth_cm_avg",
    "streamline_index",
    "entry_angle_deg_avg",
    "front_reach_distance_cm_avg",
    "elbow_angle_deg_avg",
    "forearm_drop_angle_deg_avg",
    "knee_angle_deg_avg",
    "hip_angle_deg_avg",
    "ankle_extension_angle_deg_avg",
    "kick_frequency_hz",
    "stroke_rate_spm_avg",
    "stroke_length_m_avg",
    "average_speed_mps",
    "swolf",
]


class MetricQualityEvaluator:
    def evaluate(
        self,
        metrics: dict,
        computed_keys: list[str],
        skipped_keys: list[str],
        annotation: dict | None = None,
    ) -> MetricQualityReport:
        issues: list[QualityIssue] = []
        metric_availability: dict[str, str] = {}

        for key in CORE_METRIC_KEYS:
            if key in computed_keys:
                metric_availability[key] = "available"
            elif key in skipped_keys:
                metric_availability[key] = "unavailable"
            else:
                summaries = metrics.get("summary") or metrics
                val = summaries.get(key) if isinstance(summaries, dict) else None
                if val is not None:
                    metric_availability[key] = "available"
                else:
                    metric_availability[key] = "unavailable"

        low_sample_indicators: dict[str, str] = {
            "elbow_angle_deg_avg": ELBOW_ANGLE_SAMPLE_LOW,
        }
        for key, code in low_sample_indicators.items():
            if metric_availability.get(key) == "available":
                metric_availability[key] = "low_confidence"
                issues.append(
                    QualityIssue(
                        code=code,
                        category="metrics",
                        severity="warning",
                        blocking=False,
                        path=f"metrics.{key}",
                        message=f"{key} 仅有 1 个有效样本",
                    )
                )

        unavailable_count = sum(1 for v in metric_availability.values() if v == "unavailable")
        low_confidence_count = sum(1 for v in metric_availability.values() if v == "low_confidence")

        if unavailable_count > len(CORE_METRIC_KEYS) / 2:
            status: QualityStatus = "invalid"
        elif low_confidence_count > 0 or unavailable_count > 0:
            status = "warning"
        else:
            status = "valid"

        metric_warnings = metrics.get("quality", {}).get("warnings", []) if isinstance(metrics.get("quality"), dict) else []

        return MetricQualityReport(
            schema_version="metric-quality.v1",
            status=status,
            metric_availability=metric_availability,
            issues=issues,
            computed_metric_count=len(computed_keys),
            skipped_metric_count=len(skipped_keys),
            warnings=metric_warnings,
        )
