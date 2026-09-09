"""Real-input golden backend contract coverage.

This suite deliberately calls the production ingestion, metric, artifact,
finding, and report services without replacing them with mocks.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from app.models import AnnotationFile, AnnotationFileStatus, AnnotationSource, VideoFile
from app.schemas.metrics import CALCULATOR_SIDE_2D_KINEMATICS
from app.services.normalized_annotation_service import parse_annotation_file
from app.services.diagnostics.review_findings.generation_service import generate_review_findings
from app.services.kinematic_artifacts.generation_service import generate as generate_artifacts
from app.services.metrics_service import calculate_and_persist
from app.services.reporting.kinematics_report.assembly_service import assemble_five_page_kinematics_report
from app.services.storage import StorageService
from app.core.config import get_settings
from fixtures.golden_contract import (
    assert_artifact_integrity,
    assert_finite_numbers,
    assert_five_page_contract,
    assert_no_unsupported_claims,
)
from fixtures.kinematics_golden_v1 import load_golden_fixture
from fixtures.kinematics_golden_v1.mutations import apply_mutation_recipe


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@pytest.mark.golden_contract
def test_real_golden_input_runs_through_backend_products(
    db_session,
    test_coach,
    test_session_video,
    test_video_file: VideoFile,
    monkeypatch,
    tmp_path: Path,
):
    fixture = load_golden_fixture()
    settings = get_settings()
    monkeypatch.setattr(settings, "upload_dir", tmp_path)

    test_video_file.storage_path = str(fixture.video_path)
    test_video_file.size_bytes = fixture.video_path.stat().st_size
    test_video_file.checksum_sha256 = fixture.video_sha256
    test_session_video.fps = fixture.video_fps
    test_session_video.resolution = fixture.video_resolution
    db_session.flush()

    annotation = AnnotationFile(
        session_video_id=test_session_video.id,
        source=AnnotationSource.CVAT,
        original_filename="annotations.xml",
        stored_filename="golden-annotations.xml",
        storage_path=str(fixture.annotations_path),
        file_type="xml",
        file_size_bytes=fixture.annotations_path.stat().st_size,
        checksum_sha256=_sha256(fixture.annotations_path),
        annotation_fps=fixture.video_fps,
        status=AnnotationFileStatus.UPLOADED,
        uploaded_by=test_coach.id,
        metadata={"fixture_profile": fixture.manifest["profile"]},
    )
    db_session.add(annotation)
    db_session.flush()

    parsed = parse_annotation_file(db_session, annotation.id, current_user_id=test_coach.id)
    normalized = parsed.annotation
    assert len(normalized.keypoint_frames) == fixture.active_frames
    assert normalized.annotation_metadata["frame_mapping"]["verified"] is True
    assert normalized.revision == 1

    metrics, metric_id = calculate_and_persist(
        db_session,
        normalized.id,
        persist=True,
        current_user_id=test_coach.id,
        calculator=CALCULATOR_SIDE_2D_KINEMATICS,
    )
    assert metric_id is not None
    assert_finite_numbers(metrics)

    artifact_set, _ = generate_artifacts(
        db_session,
        metric_id,
        current_user_id=test_coach.id,
    )
    finding_set, _ = generate_review_findings(
        db_session,
        metric_id,
        test_coach,
        rule_set="side_2d_kinematics_v1",
    )
    report = assemble_five_page_kinematics_report(db_session, metric_id, test_coach)
    report_data = report.model_dump(mode="json")

    assert artifact_set.source_annotation_revision == normalized.revision
    assert finding_set.source_annotation_revision == normalized.revision
    assert report_data["source_trace"]["annotation_metric"]["source_revision"] == normalized.revision
    assert report_data["source_trace"]["annotation_metric"]["revision_status"] == "current"
    assert report_data["source_trace"]["artifact_set"]["status"] == artifact_set.status
    assert report_data["source_trace"]["review_finding_set"]["status"] == finding_set.status
    assert artifact_set.status in {"ready", "partial"}
    assert finding_set.status == "ready"
    assert all(
        artifact.status == "ready" or artifact.skip_reason
        for artifact in artifact_set.artifacts
    )
    for artifact in artifact_set.artifacts:
        if artifact.status == "ready":
            assert artifact.storage_path
            path = StorageService().resolve_path(artifact.storage_path)
            assert path.is_file()
            assert artifact.mime_type
            assert artifact.size_bytes == path.stat().st_size
            assert artifact.checksum_sha256 == _sha256(path)

    assert_finite_numbers(report_data)
    assert_five_page_contract(report_data)
    assert_no_unsupported_claims(report_data)
    assert_artifact_integrity(
        asset
        for section in report_data["sections"]
        for asset in section.get("assets", [])
    )
    trace = report_data["context"].get("provenance", {}) if isinstance(report_data.get("context"), dict) else {}
    assert report_data.get("generation_signature")
    assert report_data.get("sections")


@pytest.mark.golden_contract
def test_missing_right_wrist_degrades_products_without_failing_pipeline(
    db_session,
    test_coach,
    test_session_video,
    test_video_file: VideoFile,
    monkeypatch,
    tmp_path: Path,
):
    """A declared missing-joint mutation must produce partial products, not a crash."""
    fixture = load_golden_fixture()
    mutated_xml = apply_mutation_recipe(
        fixture.mutation_recipe_paths["missing_right_wrist"],
        tmp_path / "missing_right_wrist.xml",
    )
    settings = get_settings()
    monkeypatch.setattr(settings, "upload_dir", tmp_path)

    test_video_file.storage_path = str(fixture.video_path)
    test_video_file.size_bytes = fixture.video_path.stat().st_size
    test_video_file.checksum_sha256 = fixture.video_sha256
    test_session_video.fps = fixture.video_fps
    test_session_video.resolution = fixture.video_resolution
    db_session.flush()

    annotation = AnnotationFile(
        session_video_id=test_session_video.id,
        source=AnnotationSource.CVAT,
        original_filename="missing_right_wrist.xml",
        stored_filename="missing-right-wrist.xml",
        storage_path=str(mutated_xml),
        file_type="xml",
        file_size_bytes=mutated_xml.stat().st_size,
        checksum_sha256=_sha256(mutated_xml),
        annotation_fps=fixture.video_fps,
        status=AnnotationFileStatus.UPLOADED,
        uploaded_by=test_coach.id,
        metadata={"fixture_profile": fixture.manifest["profile"]},
    )
    db_session.add(annotation)
    db_session.flush()

    parsed = parse_annotation_file(db_session, annotation.id, current_user_id=test_coach.id)
    normalized = parsed.annotation
    metrics, metric_id = calculate_and_persist(
        db_session,
        normalized.id,
        persist=True,
        current_user_id=test_coach.id,
        calculator=CALCULATOR_SIDE_2D_KINEMATICS,
    )
    assert metric_id is not None
    assert_finite_numbers(metrics)

    right_elbow = [
        point.get("value")
        for point in metrics["time_series"].get("right_elbow_angle_deg", [])
        if point.get("value") is not None
    ]
    assert not right_elbow, "missing right wrist should make the right elbow series unavailable"

    artifact_set, _ = generate_artifacts(
        db_session,
        metric_id,
        current_user_id=test_coach.id,
    )
    finding_set, _ = generate_review_findings(
        db_session,
        metric_id,
        test_coach,
        rule_set="side_2d_kinematics_v1",
    )
    report = assemble_five_page_kinematics_report(db_session, metric_id, test_coach)
    report_data = report.model_dump(mode="json")

    assert artifact_set.status == "partial"
    assert any(
        artifact.status == "skipped" and artifact.skip_reason
        for artifact in artifact_set.artifacts
    )
    assert finding_set.status == "ready"
    assert_five_page_contract(report_data)
    assert_finite_numbers(report_data)
    assert_no_unsupported_claims(report_data)
    assert report_data["status"] == "partial"
    assert any(
        section.get("page_type") == "upper_limb_kinematics"
        and section.get("status") in {"partial", "unavailable"}
        for section in report_data["sections"]
    )
