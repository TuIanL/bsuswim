"""单元测试：各检查器独立测试。"""

from app.services.annotation_quality.checks.temporal_checks import (
    check_frame_bounds,
    check_fps_consistency,
    check_event_order,
    check_event_duplicates,
)
from app.services.annotation_quality.checks.geometry_checks import (
    check_coordinate_validity,
    check_scale_validity,
)
from app.services.annotation_quality.checks.coverage_checks import (
    compute_landmark_coverage,
    check_landmark_coverage,
    check_required_events,
    check_cycle_completeness,
)


class TestFrameBounds:
    def test_all_in_range(self):
        events = [{"name": "hand_entry", "frame": 10}]
        keypoints = [{"frame": 5, "points": {}}]
        issues = check_frame_bounds(events, keypoints, 100)
        assert len(issues) == 0

    def test_event_out_of_range(self):
        events = [{"name": "hand_entry", "frame": 200}]
        issues = check_frame_bounds(events, [], 100)
        assert len(issues) == 1
        assert issues[0].code == "FRAME_OUT_OF_RANGE"
        assert issues[0].blocking is True

    def test_keypoint_out_of_range(self):
        keypoints = [{"frame": -1, "points": {}}]
        issues = check_frame_bounds([], keypoints, 100)
        assert len(issues) == 1
        assert issues[0].code == "FRAME_OUT_OF_RANGE"

    def test_no_frame_count_skips(self):
        issues = check_frame_bounds([{"frame": 200}], [], None)
        assert len(issues) == 0


class TestFpsConsistency:
    def test_exact_match(self):
        issues = check_fps_consistency(30.0, 30.0)
        assert len(issues) == 0

    def test_slight_drift_warning(self):
        issues = check_fps_consistency(31.0, 30.0)
        assert len(issues) == 1
        assert issues[0].severity == "warning"
        assert issues[0].blocking is False

    def test_large_mismatch_blocking(self):
        issues = check_fps_consistency(30.0, 60.0)
        assert len(issues) == 1
        assert issues[0].severity == "error"
        assert issues[0].blocking is True

    def test_none_skips(self):
        issues = check_fps_consistency(None, 30.0)
        assert len(issues) == 0


class TestEventOrder:
    def test_correct_order(self):
        events = [
            {"name": "hand_entry", "side": "right", "frame": 10, "label": "入水"},
            {"name": "catch_start", "side": "right", "frame": 20, "label": "抱水"},
            {"name": "pull_end", "side": "right", "frame": 30, "label": "推水"},
        ]
        issues = check_event_order(events)
        assert len(issues) == 0

    def test_reversed_order_warning(self):
        events = [
            {"name": "pull_end", "side": "right", "frame": 10, "label": "推水结束"},
            {"name": "catch_start", "side": "right", "frame": 20, "label": "抱水开始"},
            {"name": "hand_entry", "side": "right", "frame": 30, "label": "入水"},
        ]
        issues = check_event_order(events)
        assert len(issues) >= 1

    def test_multi_cycle(self):
        events = [
            {"name": "hand_entry", "side": "right", "frame": 10, "label": "入水"},
            {"name": "catch_start", "side": "right", "frame": 20, "label": "抱水"},
            {"name": "pull_end", "side": "right", "frame": 30, "label": "推水"},
            {"name": "hand_entry", "side": "right", "frame": 50, "label": "入水"},
            {"name": "catch_start", "side": "right", "frame": 60, "label": "抱水"},
            {"name": "pull_end", "side": "right", "frame": 70, "label": "推水"},
        ]
        issues = check_event_order(events)
        assert len(issues) == 0

    def test_left_right_alternating(self):
        events = [
            {"name": "hand_entry", "side": "right", "frame": 10, "label": "入水"},
            {"name": "hand_entry", "side": "left", "frame": 30, "label": "入水"},
            {"name": "catch_start", "side": "right", "frame": 20, "label": "抱水"},
            {"name": "catch_start", "side": "left", "frame": 40, "label": "抱水"},
        ]
        issues = check_event_order(events)
        assert len(issues) == 0


class TestEventDuplicates:
    def test_no_duplicates(self):
        events = [
            {"name": "hand_entry", "side": "right", "frame": 10},
            {"name": "hand_entry", "side": "right", "frame": 20},
        ]
        issues = check_event_duplicates(events)
        assert len(issues) == 0

    def test_duplicate_detected(self):
        events = [
            {"name": "hand_entry", "side": "right", "frame": 10},
            {"name": "hand_entry", "side": "right", "frame": 10},
        ]
        issues = check_event_duplicates(events)
        assert len(issues) == 1
        assert issues[0].code == "EVENT_DUPLICATED"


class TestCoordinateValidity:
    def test_valid_coordinates(self):
        kfs = [{"frame": 1, "points": {"shoulder": {"x": 100, "y": 200}}}]
        issues = check_coordinate_validity(kfs, 1920, 1080)
        assert len(issues) == 0

    def test_nan_coordinate(self):
        kfs = [{"frame": 1, "points": {"shoulder": {"x": float("nan"), "y": 200}}}]
        issues = check_coordinate_validity(kfs, 1920, 1080)
        assert len(issues) >= 1
        assert issues[0].code == "KEYPOINT_COORDINATE_INVALID"

    def test_out_of_bounds(self):
        kfs = [{"frame": 1, "points": {"shoulder": {"x": 9999, "y": 200}}}]
        issues = check_coordinate_validity(kfs, 1920, 1080)
        assert len(issues) >= 1
        assert issues[0].code == "KEYPOINT_OUT_OF_BOUNDS"


class TestScaleValidity:
    def test_valid_scale(self):
        issues = check_scale_validity({"pixels_per_meter": 100})
        assert len(issues) == 0

    def test_missing_scale(self):
        issues = check_scale_validity(None)
        assert len(issues) >= 1
        assert issues[0].code == "SCALE_INVALID"

    def test_zero_ppm(self):
        issues = check_scale_validity({"pixels_per_meter": 0})
        assert len(issues) >= 1


class TestLandmarkCoverage:
    def test_full_coverage(self):
        kfs = [{"frame": i, "points": {"shoulder": {}, "elbow": {}, "wrist": {}, "hip": {}, "knee": {}, "ankle": {}}} for i in range(10)]
        coverage = compute_landmark_coverage(kfs)
        assert coverage["shoulder"] == 1.0

    def test_partial_coverage(self):
        kfs = [{"frame": i, "points": {"shoulder": {}}} for i in range(5)] + [{"frame": i, "points": {"elbow": {}}} for i in range(3)]
        coverage = compute_landmark_coverage(kfs)
        assert coverage["shoulder"] == 5 / 8
        assert coverage["elbow"] == 3 / 8

    def test_check_low_coverage(self):
        kfs = [{"frame": i, "points": {"shoulder": {}}} for i in range(2)]
        issues = check_landmark_coverage(kfs, ["shoulder", "hip"], 0.80)
        hip_issues = [i for i in issues if "hip" in i.path]
        assert len(hip_issues) >= 1


class TestRequiredEvents:
    def test_all_present(self):
        events = [{"name": "hand_entry"}, {"name": "catch_start"}]
        issues = check_required_events(events, ["hand_entry", "catch_start"])
        assert len(issues) == 0

    def test_missing_event(self):
        events = [{"name": "hand_entry"}]
        issues = check_required_events(events, ["hand_entry", "catch_start"])
        assert len(issues) == 1
        assert issues[0].code == "EVENT_CATCH_START_MISSING"


class TestCycleCompleteness:
    def test_sufficient_cycles(self):
        events = [{"name": "hand_entry", "frame": i * 10} for i in range(3)]
        issues = check_cycle_completeness(events, min_cycles=2)
        assert len(issues) == 0

    def test_insufficient_cycles(self):
        events = [{"name": "hand_entry", "frame": 10}]
        issues = check_cycle_completeness(events, min_cycles=2)
        assert len(issues) >= 1
        assert issues[0].code == "COMPLETE_CYCLE_INSUFFICIENT"
