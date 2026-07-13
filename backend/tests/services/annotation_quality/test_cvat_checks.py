"""Tests for CVAT-specific quality checks (check_frame_mapping, check_sequence_coverage)."""

import pytest

from app.services.annotation_quality.checks.cvat_checks import (
    check_frame_mapping,
    check_sequence_coverage,
)
from app.services.annotation_quality.issue_codes import (
    SEQUENCE_COVERAGE_LOW,
    TIME_MAPPING_UNVERIFIED,
)


class TestCheckFrameMapping:
    def test_none_mapping_no_issues(self):
        issues = check_frame_mapping(None)
        assert issues == []

    def test_empty_mapping_no_issues(self):
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

    def test_unknown_unverified_no_warning(self):
        issues = check_frame_mapping({"mode": "unknown", "verified": False})
        assert issues == []


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

    def test_analysis_range_full_coverage_suppresses_warning(self):
        issues = check_sequence_coverage(
            56, 356,
            analysis_ranges=[{"start_annotation_frame": 0, "end_annotation_frame": 55}]
        )
        assert issues == []

    def test_analysis_range_partial_coverage_still_warns(self):
        issues = check_sequence_coverage(
            30, 356,
            analysis_ranges=[{"start_annotation_frame": 0, "end_annotation_frame": 55}]
        )
        assert len(issues) == 1
        assert issues[0].code == SEQUENCE_COVERAGE_LOW
