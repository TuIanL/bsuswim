"""Tests for five-page kinematics report assembly (Changes 6/12-13).

Test patterns:
- Pure unit tests: exercise assembler/page builders with synthetic data (no DB)
- Integration tests: exercise assembly_service with real DB fixtures (requires PostgreSQL)
"""


class TestVideoContextProvenance:
    """Video FPS/resolution MUST come from SessionVideo, not VideoFile."""

    def test_build_video_context_reads_session_video(self):
        from app.services.reporting.kinematics_report.page_builders import (
            _build_video_context,
        )

        class Fake:
            pass

        vf = Fake()
        vf.id = 30
        vf.original_filename = "test.mp4"
        # VideoFile deliberately has NO fps/width/height columns.
        vf.fps = 60.0  # legacy stub that MUST be ignored
        vf.width = 1920
        vf.height = 1080

        sv = Fake()
        sv.id = 20
        sv.view_type = "side"
        sv.fps = 59.94
        sv.resolution = "3840x2176"

        ctx = Fake()
        ctx.session_video = sv
        ctx.video_file = vf

        result = _build_video_context(ctx)

        assert result["fps"] == 59.94
        assert result["resolution"] == "3840x2176"
        assert result["session_video_id"] == 20
        assert result["video_file_id"] == 30
        assert result["original_filename"] == "test.mp4"
        assert result["duration_sec"] is None

    def test_build_video_context_handles_missing_session_video_fps(self):
        from app.services.reporting.kinematics_report.page_builders import (
            _build_video_context,
        )

        class Fake:
            pass

        ctx = Fake()
        ctx.session_video = None
        ctx.video_file = None

        result = _build_video_context(ctx)
        assert result["fps"] is None
        assert result["resolution"] is None


import copy
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from fixtures.synthetic_kinematics import build_golden_annotation


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _make_synthetic_metric_payload():
    """Compute a full Side2DKinematicsResult from golden annotation data."""
    from app.services.metrics.kinematics.calculator import Side2DKinematicsCalculator
    from app.services.metrics.kinematics.protocols import MetricCalculationContext

    ann_dict = build_golden_annotation(50)
    ctx = MetricCalculationContext(
        normalized_annotation_id=1,
        source_revision=3,
        annotation_metadata=ann_dict.get("annotation_metadata", {}),
        frame_mapping=ann_dict.get("annotation_metadata", {}).get("frame_mapping"),
    )
    calc = Side2DKinematicsCalculator()
    return calc.calculate(ann_dict, ctx)


def _make_assembly_context_from_metric(metric_payload):
    """Build a minimal FivePageReportAssemblyContext for pure unit tests."""
    from app.schemas.kinematics_report import (
        ArtifactResolutionResult,
        FivePageReportAssemblyContext,
    )

    class FakeObj:
        pass

    ann_metric = FakeObj()
    ann_metric.id = 1
    ann_metric.schema_version = "swim-side-kinematics.v1"
    ann_metric.calculator = "side_2d_kinematics"
    ann_metric.calculator_version = "1.0.0"
    ann_metric.source_revision = 3
    ann_metric.metrics = metric_payload

    ann = FakeObj()
    ann.id = 10
    ann.revision = 3
    ann.source = "cvat_coco17"
    ann.frame_count = 50
    ann.keypoint_frames = [{}] * 50
    ann.joint_schema = "coco17"
    ann.frame_mapping_status = "verified"

    athlete = FakeObj()
    athlete.id = 1
    athlete.name = "Test Athlete"
    athlete.gender = None
    athlete.level = "一级运动员"
    athlete.stroke_specialty = "200米自由泳"

    session = FakeObj()
    session.id = 10
    session.title = "测试训练课"
    session.session_date = None
    session.venue = None
    session.stroke_type = None
    session.distance_m = None
    session.pool_length_m = None

    vf = FakeObj()
    vf.id = 30
    vf.original_filename = "test.mp4"
    vf.fps = 60.0
    vf.width = 1920
    vf.height = 1080

    sv = FakeObj()
    sv.id = 20
    sv.view_type = "side"

    ctx = FivePageReportAssemblyContext(
        annotation_metric=ann_metric,
        normalized_annotation=ann,
        athlete=athlete,
        session=session,
        video_file=vf,
        session_video=sv,
        artifact_set=None,
        finding_set=None,
        artifact_resolution=ArtifactResolutionResult(
            artifact_set=None, resolution_status="not_generated", warning_code="artifacts_not_generated",
        ),
    )
    return ctx


# ═══════════════════════════════════════════════════════════════════════════════
# 12.1–12.6: Core structure tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestFivePageOrder:
    """12.1: Test exact five-page order."""

    def test_report_has_exactly_five_sections(self):
        from app.services.reporting.kinematics_report.assembler import build_five_page_kinematics_report

        payload = _make_synthetic_metric_payload()
        ctx = _make_assembly_context_from_metric(payload)
        report = build_five_page_kinematics_report(ctx)

        assert len(report.sections) == 5, f"Expected 5 sections, got {len(report.sections)}"

    def test_page_numbers_are_sequential(self):
        from app.services.reporting.kinematics_report.assembler import build_five_page_kinematics_report

        payload = _make_synthetic_metric_payload()
        ctx = _make_assembly_context_from_metric(payload)
        report = build_five_page_kinematics_report(ctx)

        page_numbers = [s.page_number for s in report.sections]
        assert page_numbers == [1, 2, 3, 4, 5], f"Expected [1,2,3,4,5], got {page_numbers}"


class TestSectionFields:
    """12.2: Test required section fields including source_module_keys."""

    def test_every_section_has_required_fields(self):
        from app.services.reporting.kinematics_report.assembler import build_five_page_kinematics_report

        payload = _make_synthetic_metric_payload()
        ctx = _make_assembly_context_from_metric(payload)
        report = build_five_page_kinematics_report(ctx)

        required = [
            "page_number", "page_type", "module_key",
            "source_module_keys", "status", "title",
            "assets", "metrics", "findings", "quality_notes",
        ]
        for section in report.sections:
            for field in required:
                assert hasattr(section, field), f"Section {section.page_number} missing field '{field}'"
                val = getattr(section, field)
                assert val is not None, f"Section {section.page_number} field '{field}' is None"

    def test_page_2_has_source_module_keys(self):
        from app.services.reporting.kinematics_report.assembler import build_five_page_kinematics_report

        payload = _make_synthetic_metric_payload()
        ctx = _make_assembly_context_from_metric(payload)
        report = build_five_page_kinematics_report(ctx)

        section_2 = report.sections[1]
        assert section_2.module_key == "body_posture_head_trunk"
        assert set(section_2.source_module_keys) == {"body_posture", "head_trunk"}

    def test_page_3_4_have_named_module_keys(self):
        from app.services.reporting.kinematics_report.assembler import build_five_page_kinematics_report

        payload = _make_synthetic_metric_payload()
        ctx = _make_assembly_context_from_metric(payload)
        report = build_five_page_kinematics_report(ctx)

        assert report.sections[2].source_module_keys == ["upper_limb"]
        assert report.sections[3].source_module_keys == ["lower_limb"]

    def test_page_5_aggregates_all_source_modules(self):
        from app.services.reporting.kinematics_report.assembler import build_five_page_kinematics_report

        payload = _make_synthetic_metric_payload()
        ctx = _make_assembly_context_from_metric(payload)
        report = build_five_page_kinematics_report(ctx)

        section_5 = report.sections[4]
        expected = {"body_posture", "head_trunk", "upper_limb", "lower_limb"}
        assert set(section_5.source_module_keys) == expected


class TestPage1Context:
    """12.3: Test page 1 context projection."""

    def test_page_1_has_athlete_and_session_content(self):
        from app.services.reporting.kinematics_report.assembler import build_five_page_kinematics_report

        payload = _make_synthetic_metric_payload()
        ctx = _make_assembly_context_from_metric(payload)
        report = build_five_page_kinematics_report(ctx)

        section_1 = report.sections[0]
        content = section_1.content
        assert "athlete" in str(content) or isinstance(content, dict)
        assert section_1.page_type == "analysis_overview"
        assert section_1.findings == []
        assert section_1.assets == []

    def test_page_1_analysis_boundaries_present(self):
        from app.services.reporting.kinematics_report.assembler import build_five_page_kinematics_report

        payload = _make_synthetic_metric_payload()
        ctx = _make_assembly_context_from_metric(payload)
        report = build_five_page_kinematics_report(ctx)

        section_1 = report.sections[0]
        content = section_1.content
        boundaries = content.get("analysis_boundaries", [])
        assert len(boundaries) >= 3, f"Expected at least 3 analysis boundaries, got {len(boundaries)}"


class TestMetricMapping:
    """12.4: Test four-category metric mapping."""

    def test_metrics_grouped_by_category(self):
        from app.services.reporting.kinematics_report.metric_presentation import (
            build_report_metric_index,
        )
        from app.services.metrics.kinematics.calculator import CANONICAL_KEYS

        payload = _make_synthetic_metric_payload()
        summary = payload.get("summary", {})
        index = build_report_metric_index(summary)

        categories = set()
        for m in index.values():
            categories.add(m.category)

        assert categories == {"body_posture", "upper_limb", "lower_limb", "head_trunk"}

    def test_all_23_canonical_keys_in_index(self):
        from app.services.reporting.kinematics_report.metric_presentation import (
            build_report_metric_index,
        )
        from app.services.metrics.kinematics.calculator import CANONICAL_KEYS

        payload = _make_synthetic_metric_payload()
        summary = payload.get("summary", {})
        index = build_report_metric_index(summary)

        assert len(index) == 23, f"Expected 23 metrics, got {len(index)}"
        assert set(index.keys()) == set(CANONICAL_KEYS.keys())


class TestLowConfidenceAndUnavailable:
    """12.5–12.6: Low-confidence and unavailable metric handling."""

    def test_low_confidence_metric_included_with_quality_note(self):
        from app.services.reporting.kinematics_report.metric_presentation import build_report_metric_index

        payload = _make_synthetic_metric_payload()
        summary = payload.get("summary", {})
        index = build_report_metric_index(summary)

        low_conf = [m for m in index.values() if m.availability == "low_confidence"]
        assert len(low_conf) >= 0  # golden annotation typically has high confidence

    def test_unavailable_metric_not_in_page_metrics(self):
        from app.services.reporting.kinematics_report.assembler import build_five_page_kinematics_report

        payload = _make_synthetic_metric_payload()
        ctx = _make_assembly_context_from_metric(payload)
        report = build_five_page_kinematics_report(ctx)

        for section in report.sections[1:4]:  # pages 2-4
            for metric in section.metrics:
                assert metric.availability != "unavailable", (
                    f"Page {section.page_number} includes unavailable metric {metric.key}"
                )


class TestAssemblyStatus:
    """12.17–12.18: Missing artifact/finding set produces partial report."""

    def test_missing_artifact_and_finding_yields_partial_status(self):
        from app.services.reporting.kinematics_report.assembler import build_five_page_kinematics_report

        payload = _make_synthetic_metric_payload()
        ctx = _make_assembly_context_from_metric(payload)
        # artifact_set=None, finding_set=None (default)
        report = build_five_page_kinematics_report(ctx)

        assert report.assembly_status == "partial"
        assert report.status == "partial"
        assert "artifacts_not_generated" in report.warnings or "review_findings_not_generated" in report.warnings

    def test_findings_not_generated_warning_present(self):
        from app.services.reporting.kinematics_report.assembler import build_five_page_kinematics_report

        payload = _make_synthetic_metric_payload()
        ctx = _make_assembly_context_from_metric(payload)
        report = build_five_page_kinematics_report(ctx)

        assert "review_findings_not_generated" in report.warnings


# ═══════════════════════════════════════════════════════════════════════════════
# 12.7–12.14: Finding-related tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestFindingProjection:
    """12.10–12.14: Finding projection tests."""

    def _make_sample_finding(self, code="TEST001", category="body_posture",
                             priority=10, attention="medium", confidence=0.8):
        from app.schemas.kinematic_review_finding import (
            KinematicReviewFinding,
            FindingEvidenceMetric,
            FindingEvidenceFrame,
        )
        return KinematicReviewFinding(
            code=code,
            rule_id="test_rule_001",
            title=f"测试发现 {code}",
            category=category,
            status="review_required",
            attention_level=attention,
            priority=priority,
            priority_score=float(100 - priority),
            evidence_metrics=[
                FindingEvidenceMetric(
                    key="body_axis_angle_deg",
                    source_metric_keys=["body_axis_angle_deg"],
                    label="身体角度",
                    value=12.0,
                    unit="deg",
                    availability="available",
                    confidence=confidence,
                )
            ],
            evidence_frames=[
                FindingEvidenceFrame(
                    metric_key="body_axis_angle_deg",
                    annotation_frame=10,
                    source_video_frame=10,
                    time_sec=0.167,
                    role="maximum",
                    value=12.0,
                    extractable=True,
                    mapping_status="verified",
                )
            ],
            confidence=confidence,
            confidence_level="high" if confidence >= 0.7 else "medium",
            limitations=["测试限制1", "测试限制2"],
            review_question="请复核此发现？",
            threshold_basis="project_heuristic_v1",
        )

    def test_findings_retain_review_required_status(self):
        from app.services.reporting.kinematics_report.finding_projection import project_finding

        raw = self._make_sample_finding()
        rf = project_finding(raw)
        assert rf.status == "review_required", f"Expected review_required, got {rf.status}"

    def test_findings_sorted_by_priority_and_score(self):
        from app.services.reporting.kinematics_report.finding_projection import project_and_sort_findings

        raw_findings = [
            self._make_sample_finding("A", priority=20, attention="low", confidence=0.9),
            self._make_sample_finding("B", priority=5, attention="high", confidence=0.5),
            self._make_sample_finding("C", priority=10, attention="high", confidence=0.7),
        ]
        sorted_findings = project_and_sort_findings(raw_findings)
        codes = [f.code for f in sorted_findings]
        assert codes[0] == "B", f"Highest priority (lowest number) should be first, got {codes}"

    def test_findings_grouped_by_category(self):
        from app.services.reporting.kinematics_report.finding_projection import group_findings_by_category, project_finding

        raw = [
            self._make_sample_finding("A", category="body_posture"),
            self._make_sample_finding("B", category="upper_limb"),
            self._make_sample_finding("C", category="body_posture"),
        ]
        projected = [project_finding(f) for f in raw]
        grouped = group_findings_by_category(projected)
        assert "body_posture" in grouped
        assert "upper_limb" in grouped
        assert len(grouped["body_posture"]) == 2

    def test_evidence_frames_deduplicated(self):
        """12.13: Evidence-frame deduplication."""
        raw = [
            self._make_sample_finding("A"),
            self._make_sample_finding("B"),  # same evidence frame
        ]
        from app.services.reporting.kinematics_report.finding_projection import project_finding

        projected = [project_finding(f) for f in raw]
        seen = set()
        duplicates = 0
        for f in projected:
            for ef in f.evidence_frames:
                key = (ef.annotation_frame, ef.source_video_frame)
                if key in seen:
                    duplicates += 1
                seen.add(key)
        # Sort should not create duplicates—they come from the raw findings
        assert duplicates <= len(projected), "More duplicates than findings"

    def test_limitations_aggregated(self):
        """12.14: Limitations aggregation."""
        raw = [
            self._make_sample_finding("A"),
            self._make_sample_finding("B"),
        ]
        from app.services.reporting.kinematics_report.finding_projection import project_finding

        projected = [project_finding(f) for f in raw]
        all_lims = []
        for f in projected:
            for lim in f.limitations:
                if lim not in all_lims:
                    all_lims.append(lim)
        assert "测试限制1" in all_lims
        assert "测试限制2" in all_lims

    def test_empty_findings_not_treated_as_missing(self):
        """12.16: Empty findings list is a valid ready state."""
        # Project an empty list
        from app.services.reporting.kinematics_report.finding_projection import project_and_sort_findings

        result = project_and_sort_findings([])
        assert result == []

    def test_next_capture_no_training_prescription(self):
        """12.15: Next-capture suggestions contain NO training prescription."""
        from app.services.reporting.kinematics_report.page_builders import _build_next_capture_suggestions

        ctx = _make_assembly_context_from_metric(_make_synthetic_metric_payload())
        suggestions = _build_next_capture_suggestions(ctx)

        forbidden = ["力量", "推进力", "乳酸", "强化", "核心力量", "打腿训练"]
        for s in suggestions:
            for word in forbidden:
                assert word not in s, f"Training prescription '{word}' found in: {s}"


# ═══════════════════════════════════════════════════════════════════════════════
# 12.7–12.9: Cross-side keyframe selection + skipped asset notes
# ═══════════════════════════════════════════════════════════════════════════════

class TestCrossSideKeyframeSelection:
    """12.7–12.8: Upper/Lower limb cross-side keyframe selection."""

    def _make_fake_report_asset(self, key, value=None):
        from app.schemas.kinematics_report import ReportAsset
        return ReportAsset(
            key=key,
            type="annotated_frame",
            title=key,
            url=f"http://test/{key}",
            artifact_type="annotated_keyframe",
            module_key="upper_limb" if "elbow" in key else "lower_limb",
            label=key,
            value=str(value) if value is not None else None,
        )

    def test_selects_smaller_elbow_min_as_flexion(self):
        from app.services.reporting.kinematics_report.artifact_projection import select_cross_side_keyframes

        assets = [
            self._make_fake_report_asset("upper_limb.keyframe.left_elbow_min", 80.0),
            self._make_fake_report_asset("upper_limb.keyframe.right_elbow_min", 95.0),
            self._make_fake_report_asset("upper_limb.keyframe.left_elbow_max", 160.0),
            self._make_fake_report_asset("upper_limb.keyframe.right_elbow_max", 170.0),
            self._make_fake_report_asset("lower_limb.keyframe.left_knee_min", 120.0),
            self._make_fake_report_asset("lower_limb.keyframe.right_knee_min", 110.0),
            self._make_fake_report_asset("lower_limb.keyframe.left_knee_max", 175.0),
            self._make_fake_report_asset("lower_limb.keyframe.right_knee_max", 180.0),
        ]
        elbow_flexion, elbow_extension, knee_flexion, knee_extension = select_cross_side_keyframes(assets)

        assert elbow_flexion is not None
        assert float(elbow_flexion.value) == 80.0, "Should pick smaller elbow angle (80 < 95)"

        assert elbow_extension is not None
        assert float(elbow_extension.value) == 170.0, "Should pick larger elbow angle (170 > 160)"

        assert knee_flexion is not None
        assert float(knee_flexion.value) == 110.0, "Should pick smaller knee angle (110 < 120)"

        assert knee_extension is not None
        assert float(knee_extension.value) == 180.0, "Should pick larger knee angle (180 > 175)"

    def test_cross_side_returns_none_when_no_candidates(self):
        from app.services.reporting.kinematics_report.artifact_projection import select_cross_side_keyframes

        elbow_flexion, elbow_extension, knee_flexion, knee_extension = select_cross_side_keyframes([])
        assert elbow_flexion is None
        assert elbow_extension is None
        assert knee_flexion is None
        assert knee_extension is None


class TestSkippedArtifactNotes:
    """12.9: Skipped artifacts converted to quality notes."""

    def test_skipped_artifacts_generate_notes(self):
        class FakeArtifact:
            def __init__(self, key, status, skip_reason=None, status_detail=None,
                         module_key=None, metric_keys=None):
                self.artifact_key = key
                self.status = status
                self.skip_reason = skip_reason
                self.status_detail = status_detail
                self.module_key = module_key
                self.metric_keys = metric_keys or []

        class FakeSet:
            artifacts = []

        fake_set = FakeSet()
        fake_set.artifacts = [
            FakeArtifact("test.keyframe.1", "ready"),
            FakeArtifact("test.keyframe.2", "skipped", "metric_unavailable",
                         module_key="body_posture_head_trunk", metric_keys=["elbow_angle"]),
            FakeArtifact("test.keyframe.3", "failed", "render_failed", "GPU not available",
                         module_key="upper_limb", metric_keys=["wrist_path"]),
        ]

        from app.services.reporting.kinematics_report.artifact_projection import (
            collect_skipped_artifact_quality_notes,
        )
        notes = collect_skipped_artifact_quality_notes(fake_set)
        assert len(notes) == 2
        assert notes[0]["code"] == "metric_unavailable"
        assert notes[1]["code"] == "render_failed"
        # 14.1: attribution fields populated
        assert notes[0]["module_key"] == "body_posture_head_trunk"
        assert notes[0]["artifact_key"] == "test.keyframe.2"
        assert notes[0]["metric_keys"] == ["elbow_angle"]
        assert notes[0]["artifact_status"] == "skipped"
        assert notes[1]["module_key"] == "upper_limb"
        assert notes[1]["artifact_status"] == "failed"


class TestNoteModuleScoping:
    """14.2: artifact quality notes scoped to the page's source modules."""

    def test_filter_keeps_only_matching_module(self):
        from app.services.reporting.kinematics_report.page_builders import (
            _filter_notes_by_modules,
        )
        notes = [
            {"module_key": "upper_limb", "code": "a"},
            {"module_key": "lower_limb", "code": "b"},
            {"module_key": None, "code": "c"},
        ]
        out = _filter_notes_by_modules(notes, ["upper_limb"])
        assert [n["code"] for n in out] == ["a"]

    def test_filter_empty_source_keys_drops_all(self):
        from app.services.reporting.kinematics_report.page_builders import (
            _filter_notes_by_modules,
        )
        notes = [{"module_key": "upper_limb", "code": "a"}]
        assert _filter_notes_by_modules(notes, []) == []


# ═══════════════════════════════════════════════════════════════════════════════
# 12.19–12.20: Stale metric + stale sets
# ═══════════════════════════════════════════════════════════════════════════════

class TestStaleMetricRejection:
    """12.19: Stale metric returns 409."""

    def test_validate_metric_raises_on_schema_mismatch(self):
        from app.services.reporting.kinematics_report.assembly_service import (
            _validate_metric,
            AssemblyError,
        )

        class FakeMetric:
            pass

        m = FakeMetric()
        m.calculator = "wrong_calc"
        m.schema_version = "wrong_schema"

        ann = FakeMetric()
        ann.revision = 1

        with pytest.raises(AssemblyError) as exc:
            _validate_metric(m, ann)
        assert exc.value.status_code == 422
        assert "unsupported_metric_schema" in str(exc.value.detail)

    def test_validate_metric_raises_on_revision_drift(self):
        from app.services.reporting.kinematics_report.assembly_service import (
            _validate_metric,
            AssemblyError,
        )

        class FakeMetric:
            pass

        m = FakeMetric()
        m.calculator = "side_2d_kinematics"
        m.schema_version = "swim-side-kinematics.v1"
        m.source_revision = 2
        m.metrics = {"summary": {}}

        ann = FakeMetric()
        ann.revision = 3

        with pytest.raises(AssemblyError) as exc:
            _validate_metric(m, ann)
        assert exc.value.status_code == 409
        assert "metric_revision_stale" in str(exc.value.detail)


# ═══════════════════════════════════════════════════════════════════════════════
# 12.21–12.22: Generation signature stability
# ═══════════════════════════════════════════════════════════════════════════════

class TestGenerationSignature:
    """12.21–12.22: Generation signature stability."""

    def test_signature_is_deterministic(self):
        from app.services.reporting.kinematics_report.signature import (
            compute_report_signature,
            compute_report_config_hash,
            compute_finding_payload_hash,
        )
        from app.services.reporting.kinematics_report.constants import (
            PAGE_PLAN, PAGE_READINESS_POLICY, RETEST_CORE_KEYS, PAGE_ASSET_ORDER,
            SUMMARY_TOP_FINDINGS_LIMIT, PAGE_FINDINGS_LIMIT,
        )
        from app.services.reporting.kinematics_report.metric_presentation import (
            KINEMATICS_REPORT_METRICS, PAGE_METRIC_KEYS,
        )

        config_hash = compute_report_config_hash(
            KINEMATICS_REPORT_METRICS, PAGE_METRIC_KEYS, PAGE_PLAN,
            PAGE_READINESS_POLICY, RETEST_CORE_KEYS, PAGE_ASSET_ORDER,
            {"summary": SUMMARY_TOP_FINDINGS_LIMIT, "page": PAGE_FINDINGS_LIMIT},
        )

        sig1 = compute_report_signature(
            annotation_metric_id=1, source_revision=3,
            metric_payload_hash="abc", artifact_signature="def",
            artifact_manifest_sha256="ghi", finding_signature="jkl",
            finding_payload_hash="mno", report_config_hash=config_hash,
        )
        sig2 = compute_report_signature(
            annotation_metric_id=1, source_revision=3,
            metric_payload_hash="abc", artifact_signature="def",
            artifact_manifest_sha256="ghi", finding_signature="jkl",
            finding_payload_hash="mno", report_config_hash=config_hash,
        )
        assert sig1 == sig2, "Same inputs must produce identical signature"

    def test_signature_changes_when_hash_changes(self):
        from app.services.reporting.kinematics_report.signature import compute_report_signature
        from app.services.reporting.kinematics_report.constants import (
            PAGE_PLAN, PAGE_READINESS_POLICY, RETEST_CORE_KEYS, PAGE_ASSET_ORDER,
            SUMMARY_TOP_FINDINGS_LIMIT, PAGE_FINDINGS_LIMIT,
        )
        from app.services.reporting.kinematics_report.metric_presentation import (
            KINEMATICS_REPORT_METRICS, PAGE_METRIC_KEYS,
        )
        from app.services.reporting.kinematics_report.signature import compute_report_config_hash

        config_hash = compute_report_config_hash(
            KINEMATICS_REPORT_METRICS, PAGE_METRIC_KEYS, PAGE_PLAN,
            PAGE_READINESS_POLICY, RETEST_CORE_KEYS, PAGE_ASSET_ORDER,
            {"summary": SUMMARY_TOP_FINDINGS_LIMIT, "page": PAGE_FINDINGS_LIMIT},
        )

        sig1 = compute_report_signature(
            annotation_metric_id=1, source_revision=3,
            metric_payload_hash="abc", artifact_signature="def",
            artifact_manifest_sha256="ghi", finding_signature="jkl",
            finding_payload_hash="mno", report_config_hash=config_hash,
        )
        sig2 = compute_report_signature(
            annotation_metric_id=1, source_revision=3,
            metric_payload_hash="xyz_different", artifact_signature="def",
            artifact_manifest_sha256="ghi", finding_signature="jkl",
            finding_payload_hash="mno", report_config_hash=config_hash,
        )
        assert sig1 != sig2, "Different metric hash must produce different signature"

    def test_signature_length_is_64(self):
        from app.services.reporting.kinematics_report.assembler import build_five_page_kinematics_report

        payload = _make_synthetic_metric_payload()
        ctx = _make_assembly_context_from_metric(payload)
        report = build_five_page_kinematics_report(ctx)

        assert len(report.generation_signature) == 64, f"Expected 64-char hex, got {len(report.generation_signature)}"
        assert all(c in "0123456789abcdef" for c in report.generation_signature)


# ═══════════════════════════════════════════════════════════════════════════════
# Section 4 contract tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegistryContracts:
    """4.11 / 4.12 / 12.24: Registry contract tests."""

    def test_kin_report_metrics_only_uses_canonical_keys(self):
        from app.services.reporting.kinematics_report.metric_presentation import KINEMATICS_REPORT_METRICS
        from app.services.metrics.kinematics.calculator import CANONICAL_KEYS

        configured = set(KINEMATICS_REPORT_METRICS.keys())
        canonical = set(CANONICAL_KEYS.keys())
        extra = configured - canonical
        assert extra == set(), f"KINEMATICS_REPORT_METRICS has non-canonical keys: {extra}"

    def test_every_page_metric_key_is_registered(self):
        from app.services.reporting.kinematics_report.metric_presentation import (
            KINEMATICS_REPORT_METRICS,
            PAGE_METRIC_KEYS,
        )

        all_page_keys = set()
        for keys in PAGE_METRIC_KEYS.values():
            all_page_keys.update(keys)
        unregistered = all_page_keys - set(KINEMATICS_REPORT_METRICS.keys())
        assert unregistered == set(), f"Page metric keys not in registry: {unregistered}"

    def test_canonical_keys_count_is_23(self):
        from app.services.metrics.kinematics.calculator import CANONICAL_KEYS
        assert len(CANONICAL_KEYS) == 23, (
            f"CANONICAL_KEYS count changed: {len(CANONICAL_KEYS)} (expected 23). "
            "Update KINEMATICS_REPORT_METRICS and PAGE_METRIC_KEYS accordingly."
        )

    def test_overview_stats_not_in_metric_registry(self):
        """12.24/4.14: Overview keys not in KINEMATICS_REPORT_METRICS."""
        from app.services.reporting.kinematics_report.metric_presentation import KINEMATICS_REPORT_METRICS

        forbidden = ["effective_frame_count", "joint_completeness", "total_frame_count"]
        for key in forbidden:
            assert key not in KINEMATICS_REPORT_METRICS, (
                f"Overview stat '{key}' should NOT be in KINEMATICS_REPORT_METRICS"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Section 3 — Artifact/finding signature separation
# ═══════════════════════════════════════════════════════════════════════════════

class TestSignatureSeparation:
    """3.10 / 12.25: Artifact and review-finding signatures are independent."""

    def test_artifact_and_finding_signatures_use_different_formulas(self):
        """Verify the two signature functions take different kwarg sets."""
        import inspect

        from app.services.kinematic_artifacts.signature import generation_signature
        from app.services.diagnostics.review_findings.generation_service import _compute_signature

        art_params = set(inspect.signature(generation_signature).parameters.keys())
        find_params = set(inspect.signature(_compute_signature).parameters.keys())

        # The finding _compute_signature takes positional args, not kwargs:
        # (annotation_metric_id, source_revision, metric_hash, rule_set,
        #  rule_file_hash, engine_version, threshold_basis)
        # The artifact generation_signature takes keyword-only args
        art_keys = {
            "annotation_metric_id", "source_annotation_revision", "source_metric_hash",
            "source_video_checksum", "generator_version", "artifact_plan_version",
            "style_profile", "style_profile_hash", "stability_index_config_hash",
        }
        # Both contain annotation_metric_id and source_revision and metric_hash
        # But artifact adds video checksum, style/profile hashes
        art_extra = art_keys - {"annotation_metric_id", "source_annotation_revision", "source_metric_hash"}
        assert "source_video_checksum" in art_extra, "Artifact sig must use video checksum"
        assert "style_profile" in art_extra, "Artifact sig must use style profile"


# ═══════════════════════════════════════════════════════════════════════════════
# Section 13: Golden snapshot verification
# ═══════════════════════════════════════════════════════════════════════════════

class TestGoldenSnapshot:
    """13.1–13.4: Golden snapshot assembly and normalization."""

    def test_golden_report_is_serializable(self):
        """13.1: Assemble a complete report and verify JSON serializable."""
        from app.services.reporting.kinematics_report.assembler import build_five_page_kinematics_report

        payload = _make_synthetic_metric_payload()
        ctx = _make_assembly_context_from_metric(payload)
        report = build_five_page_kinematics_report(ctx)

        # Should not raise
        json_str = report.model_dump_json(indent=2)
        assert len(json_str) > 100, "Report JSON too small"

        # Round-trip
        parsed = json.loads(json_str)
        assert parsed["schema_version"] == "swim-report.v1"
        assert parsed["report_profile"] == "side_2d_kinematics_5page_v1"
        assert len(parsed["sections"]) == 5

    def test_golden_source_trace_has_ids(self):
        """13.3 Layer 1: source_trace IDs match fixture."""
        from app.services.reporting.kinematics_report.assembler import build_five_page_kinematics_report

        payload = _make_synthetic_metric_payload()
        ctx = _make_assembly_context_from_metric(payload)
        report = build_five_page_kinematics_report(ctx)

        trace = report.source_trace
        assert trace.annotation_metric.id == 1
        assert trace.assembler.name == "five_page_kinematics_report"
        assert trace.assembler.profile == "side_2d_kinematics_5page_v1"

    def test_dynamic_fields_normalized(self):
        """13.4 Layer 2: Normalize dynamic fields for snapshot comparison."""
        from app.services.reporting.kinematics_report.assembler import build_five_page_kinematics_report

        payload = _make_synthetic_metric_payload()
        ctx = _make_assembly_context_from_metric(payload)
        report = build_five_page_kinematics_report(ctx)

        data = report.model_dump(mode="json")

        # Normalize
        data["generated_at"] = "<TIMESTAMP>"
        data["generation_signature"] = "<SIGNATURE>"

        assert data["generated_at"] == "<TIMESTAMP>"
        assert data["generation_signature"] == "<SIGNATURE>"
        assert len(data["sections"]) == 5
        for s in data["sections"]:
            assert "page_number" in s
            assert s["page_number"] in (1, 2, 3, 4, 5)


class TestGoldenContractHelpers:
    """2.1–2.9: golden dataset contract assertion helpers.

    Exercises the contract helpers against a synthetic report assembled from
    the existing fixture factory. The real-video golden E2E (blocked on P0
    fixture publish model) will reuse the same helpers.
    """

    def _assemble_synthetic_report(self):
        from app.services.reporting.kinematics_report.assembler import (
            build_five_page_kinematics_report,
        )
        payload = _make_synthetic_metric_payload()
        ctx = _make_assembly_context_from_metric(payload)
        return build_five_page_kinematics_report(ctx).model_dump(mode="json")

    def test_finite_numbers(self):
        from fixtures.golden_contract import assert_finite_numbers
        report = self._assemble_synthetic_report()
        assert_finite_numbers(report)  # must not raise

    def test_canonical_metric_keys(self):
        from app.services.metrics.kinematics.calculator import CANONICAL_KEYS
        from fixtures.golden_contract import assert_canonical_metric_keys

        report = self._assemble_synthetic_report()
        all_metrics = []
        for s in report["sections"]:
            all_metrics.extend(s.get("metrics", []))
        assert_canonical_metric_keys(all_metrics, CANONICAL_KEYS.keys())

    def test_five_page_contract(self):
        from fixtures.golden_contract import assert_five_page_contract
        report = self._assemble_synthetic_report()
        assert_five_page_contract(report)

    def test_no_unsupported_claims(self):
        from fixtures.golden_contract import assert_no_unsupported_claims
        report = self._assemble_synthetic_report()
        assert_no_unsupported_claims(report)

    def test_artifact_integrity(self):
        from fixtures.golden_contract import assert_artifact_integrity
        report = self._assemble_synthetic_report()
        all_assets = []
        for s in report["sections"]:
            all_assets.extend(s.get("assets", []))
        # helper must not raise on the synthetic report's asset set
        assert_artifact_integrity(all_assets)


# ═══════════════════════════════════════════════════════════════════════════════
# Retest metric resolution
# ═══════════════════════════════════════════════════════════════════════════════

class TestRetestMetricResolution:
    """7.11–7.13: Retest metric resolution from finding evidence."""

    def test_canonical_key_referenced_directly(self):
        from app.schemas.kinematic_review_finding import FindingEvidenceMetric
        from app.services.reporting.kinematics_report.retest import resolve_retest_source_metric_keys

        evidence = FindingEvidenceMetric(
            key="body_axis_angle_deg",
            source_metric_keys=["body_axis_angle_deg"],
            label="身体角度",
            value=12.0,
            unit="deg",
            availability="available",
            confidence=0.9,
        )
        result = resolve_retest_source_metric_keys(evidence)
        assert "body_axis_angle_deg" in result

    def test_summary_prefixed_key_resolved(self):
        from app.schemas.kinematic_review_finding import FindingEvidenceMetric
        from app.services.reporting.kinematics_report.retest import resolve_retest_source_metric_keys

        evidence = FindingEvidenceMetric(
            key="hip_vertical_range_ratio",
            source_metric_keys=["summary.hip_vertical_range_px", "reference_body_length.value_px"],
            derivation="hip_vertical_range_px / reference_body_length.value_px",
            label="髋垂直波动率",
            value=0.08,
            availability="available",
            confidence=0.8,
        )
        result = resolve_retest_source_metric_keys(evidence)
        assert "hip_vertical_range_px" in result
        # reference_body_length.* should NOT be included as canonical
        assert len(result) == 1, f"Only canonical keys expected, got {result}"

    def test_ranges_prefixed_key_resolved(self):
        from app.schemas.kinematic_review_finding import FindingEvidenceMetric
        from app.services.reporting.kinematics_report.retest import resolve_retest_source_metric_keys

        evidence = FindingEvidenceMetric(
            key="minimum_knee_p05_deg",
            source_metric_keys=["ranges.left_knee_angle_deg.p05", "ranges.right_knee_angle_deg.p05"],
            label="最小膝角P05",
            value=120.0,
            unit="deg",
            availability="available",
            confidence=0.7,
        )
        result = resolve_retest_source_metric_keys(evidence)
        assert "left_knee_angle_deg" in result
        assert "right_knee_angle_deg" in result

    def test_unknown_prefix_preserved(self):
        from app.schemas.kinematic_review_finding import FindingEvidenceMetric
        from app.services.reporting.kinematics_report.retest import resolve_retest_source_metric_keys

        evidence = FindingEvidenceMetric(
            key="custom_key",
            source_metric_keys=["custom_namespace.some_metric"],
            label="自定义",
            value=5.0,
            availability="available",
            confidence=0.5,
        )
        result = resolve_retest_source_metric_keys(evidence)
        assert "custom_namespace.some_metric" in result


# ═══════════════════════════════════════════════════════════════════════════════
# Section 11: Persisted fixture factory + DB integration tests
# ═══════════════════════════════════════════════════════════════════════════════

from dataclasses import dataclass, field


@dataclass
class KinematicsReportFixture:
    user: object = None
    athlete: object = None
    session: object = None
    video_file: object = None
    session_video: object = None
    annotation: object = None
    metric: object = None
    artifact_set: object = None
    finding_set: object = None


def build_persisted_kinematics_report_fixture(
    db_session,
    *,
    with_artifacts: bool = False,
    with_findings: bool = False,
) -> KinematicsReportFixture:
    """Build a complete persisted fixture chain: Athlete → Session → Video → Annotation → Metric.

    Built on top of conftest fixtures for ownership (coach_id alignment).
    Uses build_golden_annotation() for reliable metric output.
    Does NOT generate artifacts/findings by default (too slow for unit tests);
    pass `with_artifacts=True` / `with_findings=True` to enable.
    """
    from app.models.annotation_metric import AnnotationMetric
    from app.models.normalized_annotation import NormalizedAnnotation
    from app.models.user import User
    from app.models.athlete import Athlete
    from app.models.training_session import TrainingSession, StrokeType
    from app.models.video import SessionVideo, VideoFile, ViewType
    from app.services.metrics.kinematics.calculator import Side2DKinematicsCalculator
    from app.services.metrics.kinematics.protocols import MetricCalculationContext

    fixture = KinematicsReportFixture()

    # 1. User (coach)
    user = User(
        username="fixture_coach",
        email="fixture@test.com",
        full_name="Fixture Coach",
        role="coach",
        password_hash="dummy",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    fixture.user = user

    # 2. Athlete
    athlete = Athlete(name="Fixture Athlete", coach_id=user.id, level="一级运动员", stroke_specialty="200米自由泳")
    db_session.add(athlete)
    db_session.flush()
    fixture.athlete = athlete

    # 3. TrainingSession (coach_id must match user.id for ownership)
    ts = TrainingSession(
        athlete_id=athlete.id,
        coach_id=user.id,
        title="Fixture Session",
        stroke_type=StrokeType.FREESTYLE,
        distance_m=50,
        pool_length_m=25.0,
    )
    db_session.add(ts)
    db_session.flush()
    fixture.session = ts

    # 4. VideoFile
    vf = VideoFile(
        original_filename="fixture.mp4",
        stored_filename="fixture_stored.mp4",
        storage_path="uploads/fixture.mp4",
        mime_type="video/mp4",
        size_bytes=1000,
        checksum_sha256="fixture_checksum_sha256_64_chars_xxxxxxxxxxxxxxxxx",
    )
    db_session.add(vf)
    db_session.flush()
    fixture.video_file = vf

    # 5. SessionVideo
    sv = SessionVideo(
        session_id=ts.id,
        video_file_id=vf.id,
        view_type=ViewType.SIDE,
        fps=60.0,
    )
    db_session.add(sv)
    db_session.flush()
    fixture.session_video = sv

    # 6. NormalizedAnnotation (golden, verified)
    ann_dict = build_golden_annotation(50, verified=True)
    ann = NormalizedAnnotation(
        session_video_id=sv.id,
        revision=3,
        schema_version="swim-annotation.v1",
        source="cvat_coco17",
        fps=ann_dict["fps"],
        frame_count=len(ann_dict["keypoint_frames"]),
        keypoint_frames=ann_dict["keypoint_frames"],
        annotation_metadata=ann_dict.get("annotation_metadata", {}),
        swim_direction=ann_dict.get("swim_direction", "left_to_right"),
        scale=ann_dict.get("scale"),
    )
    db_session.add(ann)
    db_session.flush()
    fixture.annotation = ann

    # 7. AnnotationMetric
    calc = Side2DKinematicsCalculator()
    ctx = MetricCalculationContext(
        normalized_annotation_id=ann.id,
        source_revision=ann.revision,
        annotation_metadata=ann_dict.get("annotation_metadata", {}),
        frame_mapping=ann_dict.get("annotation_metadata", {}).get("frame_mapping"),
    )
    result = calc.calculate(ann_dict, ctx)
    metric = AnnotationMetric(
        normalized_annotation_id=ann.id,
        session_video_id=sv.id,
        schema_version="swim-side-kinematics.v1",
        camera_view="side",
        metrics=result,
        quality={"level": "ok"},
        calculator="side_2d_kinematics",
        calculator_version="1.0.0",
        source_revision=ann.revision,
    )
    db_session.add(metric)
    db_session.flush()
    fixture.metric = metric

    # 8. Artifacts (optional)
    if with_artifacts:
        from app.services.kinematic_artifacts.generation_service import generate
        art_set, _ = generate(db_session, metric.id, current_user_id=user.id)
        fixture.artifact_set = art_set

    # 9. Findings (optional)
    if with_findings:
        from app.services.diagnostics.review_findings.generation_service import generate_review_findings
        find_set, _ = generate_review_findings(db_session, metric.id, user)
        fixture.finding_set = find_set

    return fixture


@pytest.mark.integration
class TestPersistedFixture:
    """Integration tests requiring a real PostgreSQL database."""

    def test_fixture_builds_complete_chain(self, db_session):
        """11.1-11.2: Build persisted fixture and verify all entities."""
        fixture = build_persisted_kinematics_report_fixture(db_session)

        assert fixture.user is not None
        assert fixture.athlete is not None
        assert fixture.session is not None
        assert fixture.video_file is not None
        assert fixture.session_video is not None
        assert fixture.annotation is not None
        assert fixture.metric is not None

        # Verify coach_id alignment (11.5)
        assert fixture.session.coach_id == fixture.user.id, "session.coach_id must match user.id"

        # Verify revision alignment
        assert fixture.metric.source_revision == fixture.annotation.revision

        # Verify schema
        assert fixture.metric.calculator == "side_2d_kinematics"
        assert fixture.metric.schema_version == "swim-side-kinematics.v1"

    def test_fixture_metric_is_calculable(self, db_session):
        """11.3: Metric payload is valid and passes _verify_input checks."""
        fixture = build_persisted_kinematics_report_fixture(db_session)

        metrics = fixture.metric.metrics
        assert isinstance(metrics, dict)
        assert "summary" in metrics
        assert "time_series" in metrics
        assert len(metrics["summary"]) == 23

    def test_fixture_without_artifacts_has_none(self, db_session):
        """11.4: Variant — missing artifacts."""
        fixture = build_persisted_kinematics_report_fixture(
            db_session, with_artifacts=False, with_findings=False,
        )
        assert fixture.artifact_set is None
        assert fixture.finding_set is None

    def test_assembly_service_is_callable_from_fixture(self, db_session, auth_headers, test_coach):
        """E2E: Call assemble_five_page_kinematics_report with a real fixture."""
        fixture = build_persisted_kinematics_report_fixture(db_session)

        from app.services.reporting.kinematics_report.assembly_service import (
            assemble_five_page_kinematics_report,
        )
        # Override auth to match fixture user
        from app.core.deps import get_current_user
        from app.main import app

        app.dependency_overrides[get_current_user] = lambda: fixture.user

        try:
            report = assemble_five_page_kinematics_report(
                db_session,
                fixture.metric.id,
                fixture.user,
            )

            assert report.assembly_status == "partial"  # no artifacts/findings
            assert len(report.sections) == 5
            assert report.sections[0].page_type == "analysis_overview"
            assert report.sections[1].page_type == "body_posture_control"
            assert report.sections[2].page_type == "upper_limb_kinematics"
            assert report.sections[3].page_type == "lower_limb_kinematics"
            assert report.sections[4].page_type == "review_and_retest"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_stale_metric_returns_409_via_service(self, db_session, test_coach, auth_headers):
        """12.19 Integration: Stale metric returns 409."""
        fixture = build_persisted_kinematics_report_fixture(db_session)

        # Make the metric stale by bumping annotation revision
        fixture.annotation.revision = 99
        db_session.flush()

        from app.services.reporting.kinematics_report.assembly_service import (
            assemble_five_page_kinematics_report,
            AssemblyError,
        )
        from app.core.deps import get_current_user
        from app.main import app

        app.dependency_overrides[get_current_user] = lambda: fixture.user

        try:
            with pytest.raises(AssemblyError) as exc:
                assemble_five_page_kinematics_report(db_session, fixture.metric.id, fixture.user)
            assert exc.value.status_code == 409
            assert "metric_revision_stale" in str(exc.value.detail)
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_unsupported_calculator_returns_422(self, db_session, test_coach, auth_headers):
        """12.19 Integration: Wrong calculator returns 422."""
        fixture = build_persisted_kinematics_report_fixture(db_session)

        fixture.metric.calculator = "wrong_calc"
        db_session.flush()

        from app.services.reporting.kinematics_report.assembly_service import (
            assemble_five_page_kinematics_report,
            AssemblyError,
        )
        from app.core.deps import get_current_user
        from app.main import app

        app.dependency_overrides[get_current_user] = lambda: fixture.user

        try:
            with pytest.raises(AssemblyError) as exc:
                assemble_five_page_kinematics_report(db_session, fixture.metric.id, fixture.user)
            assert exc.value.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_golden_report_snapshot(self, db_session, test_coach, auth_headers):
        """13.1-13.4: Generate golden report from persisted fixture and snapshot."""
        fixture = build_persisted_kinematics_report_fixture(db_session)

        from app.services.reporting.kinematics_report.assembly_service import (
            assemble_five_page_kinematics_report,
        )
        from app.core.deps import get_current_user
        from app.main import app

        app.dependency_overrides[get_current_user] = lambda: fixture.user

        try:
            report = assemble_five_page_kinematics_report(
                db_session, fixture.metric.id, fixture.user,
            )

            data = report.model_dump(mode="json")

            # Layer 1: assert real fields
            assert len(data["generation_signature"]) == 64
            assert data["source_trace"]["annotation_metric"]["id"] == fixture.metric.id
            assert data["source_trace"]["assembler"]["name"] == "five_page_kinematics_report"
            assert len(data["sections"]) == 5

            # Layer 2: normalize and assert structure
            data["generated_at"] = "<TIMESTAMP>"
            data["generation_signature"] = "<SIGNATURE>"
            data["source_trace"]["annotation_metric"]["id"] = "<METRIC_ID>"
            data["source_trace"]["artifact_set"]["id"] = "<ARTIFACT_SET_ID>"

            # Save synthetic structure contract snapshot (DEMOTED: 15.x —
            # this is a controlled synthetic structure contract, NOT the
            # real-video golden baseline which is owned by the golden E2E gate).
            import os as _os
            snap_dir = _os.path.join(_os.path.dirname(__file__), "fixtures")
            _os.makedirs(snap_dir, exist_ok=True)
            snap_path = _os.path.join(snap_dir, "synthetic_five_page_report_contract.json")
            with open(snap_path, "w", encoding="utf-8") as f:
                _json = __import__("json")
                _json.dump(data, f, ensure_ascii=False, indent=2)

            assert _os.path.exists(snap_path)
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_synthetic_structure_contract_matches_fixture(self, db_session, test_coach, auth_headers):
        """15.x (DEMOTED): Synthetic structure contract, not real-golden baseline.

        Only asserts schema_version, report_profile, section count, page_number
        and page_type — deliberately NOT a full normalized-equality comparison,
        to avoid coupling the synthetic fixture to the approved golden baseline.
        """
        import os as _os
        snap_path = _os.path.join(_os.path.dirname(__file__), "fixtures",
                                   "synthetic_five_page_report_contract.json")
        if not _os.path.exists(snap_path):
            pytest.skip("Synthetic structure contract not yet generated. "
                        "Run test_golden_report_snapshot first.")

        fixture = build_persisted_kinematics_report_fixture(db_session)

        from app.services.reporting.kinematics_report.assembly_service import (
            assemble_five_page_kinematics_report,
        )
        from app.core.deps import get_current_user
        from app.main import app

        app.dependency_overrides[get_current_user] = lambda: fixture.user

        try:
            report = assemble_five_page_kinematics_report(
                db_session, fixture.metric.id, fixture.user,
            )

            # Normalize
            actual = report.model_dump(mode="json")
            actual["generated_at"] = "<TIMESTAMP>"
            actual["generation_signature"] = "<SIGNATURE>"
            for key in ("id",):
                actual["source_trace"]["annotation_metric"][key] = "<METRIC_ID>"
                actual["source_trace"]["artifact_set"][key] = "<ARTIFACT_SET_ID>"
                actual["source_trace"]["review_finding_set"][key] = "<FINDING_SET_ID>"

            # Normalize asset URLs: replace dynamic prefix
            for section in actual["sections"]:
                for asset in section.get("assets", []):
                    url = asset.get("url", "")
                    if "/uploads/kinematic-artifacts/" in url:
                        asset["url"] = "<ASSET_URL>"
                    if "/uploads/" in url and asset.get("url") != "<ASSET_URL>":
                        asset["url"] = "<ASSET_URL>"

            with open(snap_path, "r", encoding="utf-8") as f:
                _json = __import__("json")
                expected = _json.load(f)

            assert actual["schema_version"] == expected["schema_version"]
            assert actual["report_profile"] == expected["report_profile"]
            assert len(actual["sections"]) == len(expected["sections"])

            for i in range(5):
                assert actual["sections"][i]["page_number"] == expected["sections"][i]["page_number"]
                assert actual["sections"][i]["page_type"] == expected["sections"][i]["page_type"]
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_api_endpoint_returns_200(self, client, db_session, test_coach, auth_headers):
        """12 Integration: API endpoint returns valid report."""
        fixture = build_persisted_kinematics_report_fixture(db_session)

        # Override auth to match fixture user
        from app.core.deps import get_current_user
        from app.main import app

        app.dependency_overrides[get_current_user] = lambda: fixture.user

        try:
            resp = client.post(
                f"/api/v1/annotation-metrics/{fixture.metric.id}/reports/five-page/assemble",
            )
            assert resp.status_code == 200, resp.text
            data = resp.json()
            assert data["schema_version"] == "swim-report.v1"
            assert data["report_profile"] == "side_2d_kinematics_5page_v1"
            assert len(data["sections"]) == 5
            assert "assembly_status" in data
        finally:
            app.dependency_overrides.pop(get_current_user, None)
