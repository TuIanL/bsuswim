"""Tests for CVAT-specific quality checks (check_frame_mapping, check_sequence_coverage)."""

import pytest

from app.services.annotation_quality.checks.cvat_checks import (
    check_frame_mapping,
    check_fps_verified,
    check_sequence_coverage,
    contiguous_ranges_cover,
)
from app.services.annotation_quality.issue_codes import (
    ANALYSIS_RANGE_NOT_COVERED,
    FPS_UNVERIFIED,
    SEQUENCE_COVERAGE_LOW,
    TIME_MAPPING_MISSING,
    TIME_MAPPING_UNVERIFIED,
)


class TestCheckFrameMapping:
    def test_none_mapping_returns_empty_when_not_required(self):
        issues = check_frame_mapping(None)
        assert issues == []

    def test_none_mapping_returns_missing_when_required(self):
        issues = check_frame_mapping(None, required=True)
        assert len(issues) == 1
        assert issues[0].code == TIME_MAPPING_MISSING
        assert issues[0].blocking is True

    def test_empty_mapping_returns_empty_when_not_required(self):
        issues = check_frame_mapping({})
        assert issues == []

    def test_explicit_verified_no_issues(self):
        issues = check_frame_mapping({"mode": "explicit", "verified": True})
        assert issues == []

    def test_affine_unverified_emits_warning(self):
        issues = check_frame_mapping({"mode": "affine", "verified": False})
        assert len(issues) == 1
        assert issues[0].code == TIME_MAPPING_UNVERIFIED
        assert issues[0].severity == "warning"
        assert issues[0].blocking is False

    def test_identity_unverified_emits_warning(self):
        issues = check_frame_mapping({"mode": "identity", "verified": False})
        assert len(issues) == 1
        assert issues[0].code == TIME_MAPPING_UNVERIFIED

    def test_unknown_unverified_emits_warning(self):
        issues = check_frame_mapping({"mode": "unknown", "verified": False})
        assert len(issues) == 1
        assert issues[0].code == TIME_MAPPING_UNVERIFIED

    def test_explicit_unverified_emits_warning(self):
        issues = check_frame_mapping({"mode": "explicit", "verified": False})
        assert len(issues) == 1
        assert issues[0].code == TIME_MAPPING_UNVERIFIED

    def test_verified_affine_no_issues(self):
        issues = check_frame_mapping({"mode": "affine", "verified": True})
        assert issues == []

    def test_verified_identity_no_issues(self):
        issues = check_frame_mapping({"mode": "identity", "verified": True})
        assert issues == []


class TestCheckFpsVerified:
    def test_no_video_metadata_returns_empty(self):
        issues = check_fps_verified(None)
        assert issues == []

    def test_fps_verified_true_returns_empty(self):
        issues = check_fps_verified({"fps_verified": True})
        assert issues == []

    def test_fps_verified_false_emits_warning(self):
        issues = check_fps_verified({"fps_verified": False})
        assert len(issues) == 1
        assert issues[0].code == FPS_UNVERIFIED
        assert issues[0].severity == "warning"


class TestContiguousRangesCover:
    def test_exact_match_returns_true(self):
        assert contiguous_ranges_cover(
            [{"start_annotation_frame": 0, "end_annotation_frame": 55}],
            [{"start_annotation_frame": 0, "end_annotation_frame": 55}],
        ) is True

    def test_partial_overlap_returns_false(self):
        assert contiguous_ranges_cover(
            [{"start_annotation_frame": 0, "end_annotation_frame": 55}],
            [{"start_annotation_frame": 50, "end_annotation_frame": 60}],
        ) is False

    def test_disjoint_returns_false(self):
        assert contiguous_ranges_cover(
            [{"start_annotation_frame": 0, "end_annotation_frame": 20}],
            [{"start_annotation_frame": 100, "end_annotation_frame": 120}],
        ) is False

    def test_multi_range_cover(self):
        assert contiguous_ranges_cover(
            [
                {"start_annotation_frame": 0, "end_annotation_frame": 20},
                {"start_annotation_frame": 40, "end_annotation_frame": 60},
            ],
            [{"start_annotation_frame": 40, "end_annotation_frame": 60}],
        ) is True

    def test_multi_range_not_covered(self):
        assert contiguous_ranges_cover(
            [
                {"start_annotation_frame": 0, "end_annotation_frame": 20},
                {"start_annotation_frame": 40, "end_annotation_frame": 60},
            ],
            [{"start_annotation_frame": 25, "end_annotation_frame": 35}],
        ) is False

    def test_old_key_compat(self):
        assert contiguous_ranges_cover(
            [{"start_frame": 0, "end_frame": 55}],
            [{"start_annotation_frame": 0, "end_annotation_frame": 55}],
        ) is True


class TestCheckSequenceCoverage:
    def test_no_sequence_info_returns_empty(self):
        issues = check_sequence_coverage(None, None)
        assert issues == []

    def test_zero_sequence_frames_returns_empty(self):
        issues = check_sequence_coverage(56, 0)
        assert issues == []

    def test_full_coverage_returns_empty(self):
        issues = check_sequence_coverage(56, 56)
        assert issues == []

    def test_partial_coverage_emits_info(self):
        issues = check_sequence_coverage(56, 356)
        assert len(issues) == 1
        assert issues[0].code == SEQUENCE_COVERAGE_LOW
        assert issues[0].severity == "info"
        assert issues[0].blocking is False
        assert "56/356" in issues[0].message

    def test_analysis_range_covers_annotated_suppresses_warning(self):
        issues = check_sequence_coverage(
            56, 356,
            annotated_ranges=[{"start_annotation_frame": 0, "end_annotation_frame": 55}],
            analysis_ranges=[{"start_annotation_frame": 0, "end_annotation_frame": 55}],
        )
        assert issues == []

    def test_analysis_range_not_covered_emits_blocking(self):
        issues = check_sequence_coverage(
            21, 356,
            annotated_ranges=[{"start_annotation_frame": 0, "end_annotation_frame": 20}],
            analysis_ranges=[{"start_annotation_frame": 100, "end_annotation_frame": 120}],
        )
        assert len(issues) == 1
        assert issues[0].code == ANALYSIS_RANGE_NOT_COVERED
        assert issues[0].blocking is True

    def test_equal_count_but_disjoint_emits_blocking(self):
        issues = check_sequence_coverage(
            21, 356,
            annotated_ranges=[{"start_annotation_frame": 0, "end_annotation_frame": 20}],
            analysis_ranges=[{"start_annotation_frame": 100, "end_annotation_frame": 120}],
        )
        assert len(issues) == 1
        assert issues[0].code == ANALYSIS_RANGE_NOT_COVERED

    def test_no_analysis_ranges_falls_back_to_count(self):
        issues = check_sequence_coverage(
            56, 356,
            annotated_ranges=[{"start_annotation_frame": 0, "end_annotation_frame": 55}],
        )
        assert len(issues) == 1
        assert issues[0].code == SEQUENCE_COVERAGE_LOW
