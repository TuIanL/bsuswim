"""单元测试：Aggregator + combine_availability"""

from app.services.annotation_quality.aggregator import AnalysisQualityAggregator, combine_availability
from app.services.annotation_quality.models import (
    AnnotationQualityReport,
    MetricQualityReport,
    ModuleReadiness,
    QualityIssue,
    QualityProfileRef,
    QualitySummary,
)


class TestCombineAvailability:
    def test_both_ready(self):
        assert combine_availability("ready", "available") == "ready"

    def test_annotation_blocked(self):
        assert combine_availability("blocked", "available") == "blocked"

    def test_annotation_degraded_metric_good(self):
        assert combine_availability("degraded", "available") == "degraded"

    def test_annotation_ready_metric_warning(self):
        assert combine_availability("ready", "low_confidence") == "degraded"

    def test_annotation_ready_metric_unavailable(self):
        assert combine_availability("ready", "unavailable") == "blocked"


class TestAggregator:
    def _make_annotation_report(self, status: str, module_states: dict[str, str]) -> AnnotationQualityReport:
        return AnnotationQualityReport(
            status=status,
            source_revision=1,
            profile=QualityProfileRef(id="test", version="1"),
            validated_at="2026-01-01T00:00:00+00:00",
            summary=QualitySummary(),
            module_readiness={k: ModuleReadiness(status=v) for k, v in module_states.items()},
        )

    def _make_metric_report(self, avail: dict[str, str]) -> MetricQualityReport:
        return MetricQualityReport(metric_availability=avail)

    @staticmethod
    def _full_metric_avail() -> dict[str, str]:
        return {
            "body_angle_deg_avg": "available",
            "hip_depth_cm_avg": "available",
            "streamline_index": "available",
            "entry_angle_deg_avg": "available",
            "front_reach_distance_cm_avg": "available",
            "elbow_angle_deg_avg": "available",
            "forearm_drop_angle_deg_avg": "available",
            "knee_angle_deg_avg": "available",
            "hip_angle_deg_avg": "available",
            "ankle_extension_angle_deg_avg": "available",
            "kick_frequency_hz": "available",
            "stroke_rate_spm_avg": "available",
            "stroke_length_m_avg": "available",
            "average_speed_mps": "available",
            "swolf": "available",
        }

    def test_valid_annotation_good_metrics(self):
        ann_q = self._make_annotation_report("valid", {
            "body_position": "ready", "arm_entry": "ready",
            "catch_pull": "ready", "leg_kick": "ready", "efficiency": "ready",
        })
        met_q = self._make_metric_report(self._full_metric_avail())
        agg = AnalysisQualityAggregator()
        result = agg.aggregate(ann_q, met_q)
        assert result.decision.analysis_allowed is True
        assert result.decision.report_availability == "full"

    def test_annotation_valid_metric_warning(self):
        ann_q = self._make_annotation_report("valid", {
            "body_position": "ready", "arm_entry": "ready",
            "catch_pull": "ready", "leg_kick": "ready", "efficiency": "ready",
        })
        met_q = self._make_metric_report({"elbow_angle_deg_avg": "low_confidence"})
        agg = AnalysisQualityAggregator()
        result = agg.aggregate(ann_q, met_q)
        assert result.decision.report_availability == "degraded"

    def test_invalid_annotation(self):
        ann_q = self._make_annotation_report("invalid", {
            "body_position": "blocked", "arm_entry": "blocked",
            "catch_pull": "blocked", "leg_kick": "blocked", "efficiency": "blocked",
        })
        agg = AnalysisQualityAggregator()
        result = agg.aggregate(ann_q, None)
        assert result.decision.analysis_allowed is False
        assert result.decision.report_availability == "blocked"

    def test_non_core_blocked_still_warning(self):
        ann_q = self._make_annotation_report("warning", {
            "body_position": "ready", "arm_entry": "ready",
            "catch_pull": "ready", "leg_kick": "blocked", "efficiency": "blocked",
        })
        met_q = self._make_metric_report(self._full_metric_avail())
        agg = AnalysisQualityAggregator()
        result = agg.aggregate(ann_q, met_q)
        assert result.decision.analysis_allowed is True
        assert result.decision.report_availability == "degraded"
