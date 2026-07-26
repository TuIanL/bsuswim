import pytest
from fastapi import HTTPException

from app.schemas.normalized_annotation import EventRepair, FrameMappingOverride, RepairPoint
from app.services.annotation_quality.repair_service import _build_frame_mapping, _merge_events, _validate_points
from app.services.annotation_quality.validator import AnnotationQualityValidator
from app.services.annotation_quality.provider import YamlQualityProfileProvider


def test_validate_points_keeps_intrinsic_pixel_coordinates():
    points = _validate_points(
        [RepairPoint(x=10, y=20), RepairPoint(x=110, y=20)],
        200,
        100,
    )
    assert points == [[10.0, 20.0], [110.0, 20.0]]


def test_validate_points_rejects_out_of_bounds():
    with pytest.raises(HTTPException):
        _validate_points([RepairPoint(x=-1, y=20), RepairPoint(x=110, y=20)], 200, 100)


def test_merge_events_deduplicates_and_sorts():
    events = _merge_events(
        [{"name": "hand_entry", "frame": 20, "side": "unknown", "time_sec": 0.2}],
        [
            EventRepair(name="hand_entry", label="入水", frame=20, time_sec=0.2),
            EventRepair(name="hand_entry", label="入水", frame=10, time_sec=0.1),
        ],
    )
    assert [event["frame"] for event in events] == [10, 20]


def test_quality_issue_contains_repair_action():
    validator = AnnotationQualityValidator(
        profile_provider=YamlQualityProfileProvider("app/services/annotation_quality/profiles")
    )
    report = validator.validate(
        events=[],
        keypoint_frames=[{"frame": 0, "points": {}}],
        scale=None,
        fps=60,
        frame_count=1,
        reference_lines=None,
        swim_direction=None,
    )
    actions = {issue.code: issue.suggested_action.type for issue in report.issues if issue.suggested_action}
    assert actions["SCALE_INVALID"] == "scale"
    assert actions["WATERLINE_MISSING"] == "waterline"


def test_frame_mapping_confirmation_sets_user_provenance():
    mapping = _build_frame_mapping(
        FrameMappingOverride(mode="affine", source_frame_offset=32, source_frame_stride=1, confirmed=True),
        60,
    )
    assert mapping["verified"] is True
    assert mapping["verification_reason"] == "user_confirmed"


def test_unconfirmed_identity_mapping_stays_unverified():
    mapping = _build_frame_mapping(FrameMappingOverride(mode="identity", confirmed=False), 60)
    assert mapping["verified"] is False
    assert mapping["verification_reason"] == "user_provided_not_confirmed"


def test_affine_mapping_rejects_non_positive_stride():
    with pytest.raises(HTTPException):
        _build_frame_mapping(
            FrameMappingOverride(mode="affine", source_frame_offset=0, source_frame_stride=0),
            60,
        )
