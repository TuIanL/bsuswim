"""Contract tests for the guided side-2D kinematics workflow (Change 8).

Covers backend read-contract extensions:
- annotation list returns parse summary / quality / module readiness
- analysis status returns real pipeline metadata + ordered pipeline_progress
- analysis list filtering by session / pipeline / limit
- retryable processing failure exposes `retry`
- revision drift exposes `resubmit`
- concurrent submit returns 409 with existing_task_id (PostgreSQL)
"""
import pytest

from app.models import AnalysisTask, AnalysisTaskStatus, AnnotationFile, AnnotationFileStatus
from app.models.annotation import AnnotationSource
from app.models.normalized_annotation import NormalizedAnnotation
from app.schemas.analysis import ANNOTATION_PIPELINE_VERSION
from app.services.analysis_service import (
    AnalysisTaskAlreadyActiveError,
    create_analysis_task,
    read_analysis_task,
    task_actions,
)
from app.schemas.analysis import AnalysisSubmit


def _make_annotation_file(db_session, session_video, status=AnnotationFileStatus.PARSED):
    af = AnnotationFile(
        session_video_id=session_video.id,
        source="cvat",
        original_filename="skeleton.xml",
        stored_filename="skeleton.xml",
        storage_path="/tmp/skeleton.xml",
        file_type="xml",
        file_size_bytes=1024,
        checksum_sha256="abc",
        status=status,
        version=1,
    )
    db_session.add(af)
    db_session.flush()
    return af


def _submit(db_session, session_id, normalized_annotation_id, pipeline_type="annotation_kinematics"):
    # 确保标注有可用质量（测试 fixture 不自动生成 quality）
    ann = db_session.get(NormalizedAnnotation, normalized_annotation_id)
    if ann and (not ann.quality or ann.quality.get("status") in (None, "error", "invalid")):
        ann.quality = {
            "schema_version": "annotation-quality.v2",
            "status": "valid",
            "score": 90,
            "module_readiness": {
                "body_position": {"status": "ready"},
                "arm_entry": {"status": "ready"},
                "catch_pull": {"status": "ready"},
                "leg_kick": {"status": "ready"},
                "efficiency": {"status": "ready"},
            },
        }
        db_session.commit()
    payload = AnalysisSubmit(
        session_id=session_id,
        normalized_annotation_id=normalized_annotation_id,
        acknowledge_quality_warnings=True,
        pipeline_type=pipeline_type,
        pipeline_version=ANNOTATION_PIPELINE_VERSION,
    )
    return create_analysis_task(db_session, payload)


def test_annotation_list_returns_parse_and_quality(db_session, client, auth_headers, test_session, test_session_video, test_normalized_annotation):
    _make_annotation_file(db_session, test_session_video)
    af = db_session.query(AnnotationFile).filter_by(session_video_id=test_session_video.id).first()
    test_normalized_annotation.annotation_file_id = af.id
    test_normalized_annotation.quality = {
        "schema_version": "annotation-quality.v2",
        "status": "valid",
        "score": 90,
        "module_readiness": {
            "body_position": {"status": "ready"},
            "arm_entry": {"status": "ready"},
            "catch_pull": {"status": "ready"},
            "leg_kick": {"status": "ready"},
            "efficiency": {"status": "ready"},
        },
    }
    db_session.commit()

    resp = client.get(
        f"/api/v1/sessions/{test_session.id}/videos/{test_session_video.video_file_id}/annotations",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    items = resp.json()
    assert items
    item = next(i for i in items if i["normalized_annotation_id"] == test_normalized_annotation.id)
    assert item["parse_summary"] is not None
    assert item["quality"] is not None
    assert item["kinematics_module_readiness"]
    assert set(item["kinematics_module_readiness"].keys()) == {
        "body_posture", "upper_limb", "lower_limb", "head_trunk"
    }
    for v in item["kinematics_module_readiness"].values():
        assert v in ("ready", "degraded", "blocked")


def test_analysis_status_returns_pipeline_progress(db_session, client, auth_headers, test_session, test_session_video, test_normalized_annotation):
    task = _submit(db_session, test_session.id, test_normalized_annotation.id)
    db_session.commit()
    resp = client.get(f"/api/v1/analysis/{task.id}/status", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["pipeline_type"] == "annotation_kinematics"
    assert body["pipeline_version"] == ANNOTATION_PIPELINE_VERSION
    assert "pipeline_progress" in body
    assert body["pipeline_progress"]["steps"]
    for s in body["pipeline_progress"]["steps"]:
        assert s["status"] in ("pending", "running", "completed", "failed")


def test_analysis_list_filters(db_session, client, auth_headers, test_session, test_session_video, test_normalized_annotation):
    task = _submit(db_session, test_session.id, test_normalized_annotation.id)
    db_session.commit()
    resp = client.get(
        f"/api/v1/analysis?session_id={test_session.id}&pipeline_type=annotation_kinematics&limit=1",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["id"] == task.id


def test_processing_failure_exposes_retry(db_session, test_session, test_session_video, test_normalized_annotation):
    task = _submit(db_session, test_session.id, test_normalized_annotation.id)
    task.status = AnalysisTaskStatus.FAILED
    task.failed_stage = "generating_artifacts"
    task.error_code = "ARTIFACT_GENERATION_FAILED"
    db_session.commit()
    assert task_actions(task) == ["retry", "details"]


def test_revision_drift_exposes_resubmit(db_session, test_session, test_session_video, test_normalized_annotation):
    task = _submit(db_session, test_session.id, test_normalized_annotation.id)
    task.status = AnalysisTaskStatus.FAILED
    task.failed_stage = "validating_input"
    task.error_code = "ANNOTATION_REVISION_DRIFT"
    db_session.commit()
    assert task_actions(task) == ["resubmit", "details"]


def test_concurrent_active_task_raises(db_session, test_session, test_session_video, test_normalized_annotation):
    task = _submit(db_session, test_session.id, test_normalized_annotation.id)
    task.status = AnalysisTaskStatus.PROCESSING
    db_session.commit()
    with pytest.raises(AnalysisTaskAlreadyActiveError) as exc:
        _submit(db_session, test_session.id, test_normalized_annotation.id)
    assert exc.value.existing_task_id == task.id


def test_concurrent_active_task_returns_409(db_session, client, auth_headers, test_session, test_session_video, test_normalized_annotation):
    task = _submit(db_session, test_session.id, test_normalized_annotation.id)
    task.status = AnalysisTaskStatus.PROCESSING
    db_session.commit()
    resp = client.post(
        "/api/v1/analysis/submit",
        json={
            "session_id": test_session.id,
            "normalized_annotation_id": test_normalized_annotation.id,
            "acknowledge_quality_warnings": True,
            "pipeline_type": "annotation_kinematics",
            "pipeline_version": ANNOTATION_PIPELINE_VERSION,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["error"]["code"] == "ANALYSIS_TASK_ALREADY_ACTIVE"
    assert resp.json()["detail"]["error"]["existing_task_id"] == task.id


def test_completed_without_report_synthesizes_metadata_missing(db_session, test_session, test_session_video, test_normalized_annotation):
    task = _submit(db_session, test_session.id, test_normalized_annotation.id)
    task.status = AnalysisTaskStatus.COMPLETED
    db_session.commit()
    # 未创建 ReportMetadata -> read 契约应合成 REPORT_METADATA_MISSING
    payload = read_analysis_task(task, db_session)
    assert payload.error_code == "REPORT_METADATA_MISSING"
    assert payload.failed_stage == "assembling_report"
    # 且动作应允许 resubmit（使用当前标注重新生成）
    assert "resubmit" in payload.actions

