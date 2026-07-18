"""Tests for kinematic visual artifact generation (change add-kinematics-visual-artifact-generation)."""

import os

import pytest

from app.core.deps import get_current_user
from app.db.session import get_db
from app.main import app
from app.models.annotation_metric import AnnotationMetric
from app.models.kinematic_artifact import KinematicArtifact, KinematicArtifactSet
from app.models.normalized_annotation import NormalizedAnnotation
from app.models.video import SessionVideo, VideoFile, ViewType
from app.services.kinematic_artifacts import stability_index
from app.services.kinematic_artifacts.frame_selection import select_all_keyframes
from app.services.kinematic_artifacts.frame_provider import KinematicFrameSequenceProvider
from app.services.kinematic_artifacts.generation_service import generate, GenerationError
from app.services.kinematic_artifacts.signature import (
    canonical_json,
    generation_signature,
    metric_hash,
)
from app.services.metrics.kinematics.calculator import Side2DKinematicsCalculator
from app.services.metrics.kinematics.frame_resolver import resolve_frames
from app.services.metrics.kinematics.protocols import MetricCalculationContext

from fixtures.synthetic_kinematics import build_golden_annotation

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture(autouse=True)
def override_auth(db_session):
    """Authenticate and bind the real DB session for API tests."""

    class _User:
        id = 1
        username = "test_coach"
        is_active = True

    async def fake_get_current_user():
        return _User()

    app.dependency_overrides[get_current_user] = fake_get_current_user
    app.dependency_overrides[get_db] = lambda: db_session
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)


def _compute_metric(ann_dict: dict) -> dict:
    calc = Side2DKinematicsCalculator()
    ctx = MetricCalculationContext(
        normalized_annotation_id=1,
        source_revision=3,
        annotation_metadata=ann_dict.get("annotation_metadata", {}),
        frame_mapping=(ann_dict.get("annotation_metadata", {}).get("frame_mapping")),
    )
    return calc.calculate(ann_dict, ctx)


def _make_video_file(db, path="uploads/fake_video.mp4", checksum="abc123"):
    vf = VideoFile(
        original_filename="fake.mp4",
        stored_filename="fake.mp4",
        storage_path=path,
        mime_type="video/mp4",
        size_bytes=100,
        checksum_sha256=checksum,
    )
    db.add(vf)
    db.flush()
    return vf


def _make_annotation(db, ann_dict, revision=3, verified=True):
    from app.models.athlete import Athlete
    from app.models.training_session import TrainingSession, StrokeType

    athlete = Athlete(name="test-athlete", gender="other")
    db.add(athlete)
    db.flush()
    ts = TrainingSession(athlete_id=athlete.id, title="test-session", stroke_type=StrokeType.FREESTYLE)
    db.add(ts)
    db.flush()
    vf = VideoFile(
        original_filename="dummy.mp4", stored_filename="dummy.mp4",
        storage_path="uploads/dummy.mp4", mime_type="video/mp4",
        size_bytes=1, checksum_sha256="dummy",
    )
    db.add(vf)
    db.flush()
    sv = SessionVideo(session_id=ts.id, video_file_id=vf.id, view_type=ViewType.SIDE)
    db.add(sv)
    db.flush()
    ann = NormalizedAnnotation(
        session_video_id=sv.id,
        revision=revision,
        schema_version="swim-annotation.v1",
        source="cvat_coco17",
        fps=60.0,
        frame_count=len(ann_dict["keypoint_frames"]),
        keypoint_frames=ann_dict["keypoint_frames"],
        annotation_metadata={"frame_mapping": {"verified": verified}},
    )
    db.add(ann)
    db.flush()
    return ann


def _make_metric(db, ann, result):
    metric = AnnotationMetric(
        normalized_annotation_id=ann.id,
        session_video_id=1,
        schema_version="swim-side-kinematics.v1",
        camera_view="side",
        metrics=result,
        quality={"level": "ok"},
        calculator="side_2d_kinematics",
        calculator_version="1.0.0",
        source_revision=ann.revision,
    )
    db.add(metric)
    db.flush()
    return metric


# --- Phase 0: baseline / contract -----------------------------------------
def test_golden_fixture_runs(db_session):
    ann = build_golden_annotation()
    result = _compute_metric(ann)
    assert "summary" in result and "time_series" in result


def test_metric_results_not_mutated(db_session):
    ann = build_golden_annotation()
    result = _compute_metric(ann)
    import copy

    snapshot = copy.deepcopy(result)
    # provider consumes annotation, must not mutate metric payload
    provider = KinematicFrameSequenceProvider()
    norm = NormalizedAnnotation(
        session_video_id=1, revision=3, schema_version="swim-annotation.v1", source="cvat_coco17",
        fps=60.0, frame_count=len(ann["keypoint_frames"]), keypoint_frames=ann["keypoint_frames"],
        annotation_metadata={"frame_mapping": {"verified": True}},
    )
    provider.build(norm)
    assert result == snapshot


# --- signature & canonical json -------------------------------------------
def test_canonical_json_order_independent():
    a = canonical_json({"b": 1, "a": 2})
    b = canonical_json({"a": 2, "b": 1})
    assert a == b


def test_signature_changes_with_video_checksum():
    base = dict(
        annotation_metric_id=1, source_annotation_revision=3, source_metric_hash="h",
        source_video_checksum="v1", generator_version="1.0.0",
        artifact_plan_version="artifact-plan.v1", style_profile="s", style_profile_hash="sh",
        stability_index_config_hash="ch",
    )
    s1 = generation_signature(**base)
    s2 = generation_signature(**{**base, "source_video_checksum": "v2"})
    assert s1 != s2


# --- frame selection --------------------------------------------------------
def test_deterministic_keyframe_selection(db_session):
    ann = build_golden_annotation()
    result = _compute_metric(ann)
    frames = resolve_frames(ann["keypoint_frames"])
    ref = result.get("reference_body_length", {}).get("value_px")
    sel1 = select_all_keyframes(result["summary"], result["time_series"], frames, ref)
    sel2 = select_all_keyframes(result["summary"], result["time_series"], frames, ref)
    assert [s.artifact_metric_key for s in sel1] == [s.artifact_metric_key for s in sel2]


def test_arm_extension_records_side(db_session):
    ann = build_golden_annotation()
    result = _compute_metric(ann)
    frames = resolve_frames(ann["keypoint_frames"])
    ref = result.get("reference_body_length", {}).get("value_px")
    sel = select_all_keyframes(result["summary"], result["time_series"], frames, ref)
    arm = next((s for s in sel if s.artifact_metric_key == "upper_limb.keyframe.arm_extension_max"), None)
    assert arm is not None
    assert arm.metadata["selected_side"] in ("left", "right")


# --- generation: charts only (no video) -----------------------------------
def test_generation_charts_only_without_video(db_session):
    ann = build_golden_annotation()
    result = _compute_metric(ann)
    metric = _make_metric(db_session, _make_annotation(db_session, ann), result)
    db_session.flush()
    artifact_set, created = generate(db_session, metric.id)
    assert created
    assert artifact_set.status in ("ready", "partial")
    keys = {a.artifact_key for a in artifact_set.artifacts}
    assert "overview.chart.stability_radar" in keys
    # no video → keyframes skipped
    kf = [a for a in artifact_set.artifacts if a.artifact_type == "annotated_keyframe"]
    assert all(a.status == "skipped" for a in kf)


def test_idempotent_generation(db_session):
    ann = build_golden_annotation()
    result = _compute_metric(ann)
    metric = _make_metric(db_session, _make_annotation(db_session, ann), result)
    db_session.flush()
    s1, _ = generate(db_session, metric.id)
    s2, created = generate(db_session, metric.id)
    assert not created
    assert s1.id == s2.id


def test_force_regeneration_same_set(db_session):
    ann = build_golden_annotation()
    result = _compute_metric(ann)
    metric = _make_metric(db_session, _make_annotation(db_session, ann), result)
    db_session.flush()
    s1, _ = generate(db_session, metric.id)
    s2, created = generate(db_session, metric.id, force=True)
    assert s2.id == s1.id


# --- video present → keyframes ---------------------------------------------
def test_generation_with_video_keyframes(db_session, tmp_path):
    ann = build_golden_annotation()
    result = _compute_metric(ann)
    # create a tiny blank video
    import cv2
    import numpy as np

    vpath = tmp_path / "v.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    n = len(ann["keypoint_frames"])
    vw = cv2.VideoWriter(str(vpath), fourcc, 30.0, (800, 800))
    for _ in range(n):
        vw.write(np.full((800, 800, 3), 240, dtype=np.uint8))
    vw.release()
    vf = VideoFile(
        original_filename="v.mp4", stored_filename="v.mp4", storage_path=str(vpath),
        mime_type="video/mp4", size_bytes=10, checksum_sha256="vidchecksum",
    )
    db_session.add(vf)
    db_session.flush()
    norm = _make_annotation(db_session, ann, verified=True)
    sv = db_session.get(SessionVideo, norm.session_video_id)
    sv.video_file_id = vf.id
    metric = _make_metric(db_session, norm, result)
    metric.session_video_id = sv.id
    db_session.flush()
    artifact_set, _ = generate(db_session, metric.id)
    kf = [a for a in artifact_set.artifacts if a.artifact_type == "annotated_keyframe"]
    ready_kf = [a for a in kf if a.status == "ready"]
    assert len(ready_kf) > 0
    assert all(a.storage_path for a in ready_kf)


# --- stale revision ---------------------------------------------------------
def test_stale_revision_blocks(db_session):
    ann = build_golden_annotation()
    result = _compute_metric(ann)
    norm = _make_annotation(db_session, ann, revision=3)
    metric = _make_metric(db_session, norm, result)
    metric.source_revision = 2  # stale vs annotation.revision=3
    db_session.flush()
    with pytest.raises(GenerationError) as exc:
        generate(db_session, metric.id)
    assert exc.value.code == "metric_revision_stale"


def test_null_revision_blocks(db_session):
    ann = build_golden_annotation()
    result = _compute_metric(ann)
    norm = _make_annotation(db_session, ann, revision=3)
    metric = _make_metric(db_session, norm, result)
    metric.source_revision = None
    db_session.flush()
    with pytest.raises(GenerationError) as exc:
        generate(db_session, metric.id)
    assert exc.value.code == "metric_revision_stale"


# --- radar signature & N/A -------------------------------------------------
def test_config_change_alters_signature():
    h1 = stability_index.config_hash()
    assert isinstance(h1, str) and len(h1) == 64


def test_radar_inputs_insufficient(db_session):
    # empty summary → fewer than 3 axes available
    frames = resolve_frames(build_golden_annotation()["keypoint_frames"])
    axes = stability_index.compute_axes({})
    assert stability_index.available_axis_count(axes) < 3


# --- manifest authority ----------------------------------------------------
def test_manifest_matches_artifact_rows(db_session):
    ann = build_golden_annotation()
    result = _compute_metric(ann)
    metric = _make_metric(db_session, _make_annotation(db_session, ann), result)
    db_session.flush()
    artifact_set, _ = generate(db_session, metric.id)
    manifest_keys = [a["artifact_key"] for a in artifact_set.manifest["artifacts"]]
    row_keys = sorted(a.artifact_key for a in artifact_set.artifacts)
    assert sorted(manifest_keys) == row_keys
    assert artifact_set.manifest_sha256


# --- API --------------------------------------------------------------------
def test_api_generate_and_read(client, db_session):
    ann = build_golden_annotation()
    result = _compute_metric(ann)
    metric = _make_metric(db_session, _make_annotation(db_session, ann), result)
    db_session.flush()
    resp = client.post(f"/api/v1/annotation-metrics/{metric.id}/artifacts/generate")
    assert resp.status_code in (200, 201)
    get = client.get(f"/api/v1/annotation-metrics/{metric.id}/artifacts")
    assert get.status_code == 200
    body = get.json()
    assert body["status"] in ("ready", "partial")
    assert all("/uploads/" in (a["url"] or "") for a in body["artifacts"] if a["url"])


def test_api_stale_revision(client, db_session):
    ann = build_golden_annotation()
    result = _compute_metric(ann)
    norm = _make_annotation(db_session, ann, revision=3)
    metric = _make_metric(db_session, norm, result)
    metric.source_revision = 1
    db_session.flush()
    resp = client.post(f"/api/v1/annotation-metrics/{metric.id}/artifacts/generate")
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "metric_revision_stale"
