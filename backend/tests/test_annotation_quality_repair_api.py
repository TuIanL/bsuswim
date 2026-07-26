"""Integration coverage for the annotation quality repair contract."""

from app.models import User


def _payload(revision: int) -> dict:
    return {
        "expected_revision": revision,
        "scale": {
            "points": [{"x": 100, "y": 100}, {"x": 500, "y": 100}],
            "reference_length_m": 10,
            "method": "manual_reference",
        },
        "waterline": {
            "points": [{"x": 0, "y": 300}, {"x": 1000, "y": 300}],
        },
        "swim_direction": "left_to_right",
        "events": [
            {"name": "hand_entry", "label": "入水", "frame": 10, "time_sec": 0.167},
            {"name": "hand_entry", "label": "入水", "frame": 40, "time_sec": 0.667},
        ],
        "frame_mapping": {
            "mode": "affine",
            "source_frame_offset": 2,
            "source_frame_stride": 1,
            "confirmed": True,
        },
    }


def _prepare_annotation(test_session_video, test_normalized_annotation):
    test_session_video.resolution = "3840x2160"
    test_session_video.fps = 60
    annotation = test_normalized_annotation
    annotation.scale = None
    annotation.reference_lines = None
    annotation.events = []
    annotation.swim_direction = None
    annotation.annotation_metadata = {"video": {"width": 3840, "height": 2160}}
    annotation.quality = {}
    return annotation


def test_quality_repair_api_revalidates_and_returns_latest_readiness(
    client,
    auth_headers,
    test_session_video,
    test_normalized_annotation,
):
    annotation = _prepare_annotation(test_session_video, test_normalized_annotation)

    response = client.post(
        f"/api/v1/normalized-annotations/{annotation.id}/quality-repair",
        json=_payload(annotation.revision),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["normalized_annotation_id"] == annotation.id
    assert data["revision"] == 2
    assert data["quality"]["source_revision"] == 2
    assert isinstance(data["analysis_readiness"]["can_submit"], bool)
    assert data["module_readiness"]
    assert data["quality"]["issues"]

    assert annotation.revision == 2
    assert annotation.swim_direction == "left_to_right"
    assert annotation.annotation_metadata["frame_mapping"]["verified"] is True


def test_quality_repair_api_rejects_stale_revision_without_writing(
    client,
    auth_headers,
    test_session_video,
    test_normalized_annotation,
):
    annotation = _prepare_annotation(test_session_video, test_normalized_annotation)
    before = annotation.revision

    response = client.post(
        f"/api/v1/normalized-annotations/{annotation.id}/quality-repair",
        json={"expected_revision": before + 1, "swim_direction": "right_to_left"},
    )

    assert response.status_code == 409
    assert annotation.revision == before
    assert annotation.swim_direction is None


def test_quality_repair_api_enforces_annotation_ownership(
    client,
    auth_headers,
    db_session,
    test_session,
    test_session_video,
    test_normalized_annotation,
):
    outsider = User(
        username="repair_outsider",
        email="repair_outsider@test.com",
        full_name="Repair Outsider",
        role="coach",
        password_hash="dummy",
        is_active=True,
    )
    db_session.add(outsider)
    db_session.flush()
    test_session.coach_id = outsider.id
    _prepare_annotation(test_session_video, test_normalized_annotation)

    response = client.post(
        f"/api/v1/normalized-annotations/{test_normalized_annotation.id}/quality-repair",
        json={"expected_revision": 1, "swim_direction": "left_to_right"},
    )

    assert response.status_code == 404


def test_quality_repair_full_flow_preserves_remaining_quality_gates(
    client,
    auth_headers,
    test_session_video,
    test_normalized_annotation,
):
    annotation = _prepare_annotation(test_session_video, test_normalized_annotation)

    response = client.post(
        f"/api/v1/normalized-annotations/{annotation.id}/quality-repair",
        json=_payload(annotation.revision),
    )

    data = response.json()
    codes = {issue["code"] for issue in data["quality"]["issues"]}
    assert response.status_code == 200
    assert "SCALE_MISSING" not in codes
    assert "WATERLINE_MISSING" not in codes
    assert "SWIM_DIRECTION_UNSET" not in codes
    assert data["quality"]["source_revision"] == data["revision"]
    assert "module_readiness" in data["quality"]
    assert isinstance(data["analysis_readiness"]["affected_modules"], list)
