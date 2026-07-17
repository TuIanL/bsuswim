"""side_2d_kinematics 的 API / 持久化集成测试（需要 Postgres）。

覆盖 tasks 11.x / 12.18 / 12.19 / 12.20 / 13.3：
- POST calculate-metrics?calculator=side_2d_kinematics 并 persist
- GET metrics 按 calculator 过滤
- revision_status 三态（current / stale / unknown）
- 旧记录 source_revision=NULL 仍可读（unknown 而非 stale）
- 未知 calculator → 422 unsupported_metric_calculator
- 旧 side_view_metrics 调用保持向后兼容
"""

import pytest

from app.models import AnnotationMetric

pytestmark = pytest.mark.integration


def _seed_annotation(db_session, test_session_video, revision=1):
    from fixtures.synthetic_kinematics import build_synthetic_annotation
    from app.models.normalized_annotation import NormalizedAnnotation

    ann = build_synthetic_annotation(96)
    record = NormalizedAnnotation(
        session_video_id=test_session_video.id,
        revision=revision,
        schema_version="swim-annotation.v1",
        source="cvat",
        fps=ann["fps"],
        frame_count=len(ann["keypoint_frames"]),
        scale=ann["scale"],
        keypoint_frames=ann["keypoint_frames"],
        annotation_metadata={"stroke_type": "freestyle"},
        swim_direction=ann["swim_direction"],
    )
    db_session.add(record)
    db_session.flush()
    return record


def test_calculate_persists_side_2d_kinematics(client, auth_headers, db_session, test_session_video):
    ann = _seed_annotation(db_session, test_session_video)
    resp = client.post(
        f"/api/v1/normalized-annotations/{ann.id}/calculate-metrics"
        f"?persist=true&calculator=side_2d_kinematics",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["calculator"] == "side_2d_kinematics"
    assert body["schema_version"] == "swim-side-kinematics.v1"
    assert body["annotation_metric_id"] is not None

    rec = db_session.get(AnnotationMetric, body["annotation_metric_id"])
    assert rec is not None
    assert rec.calculator == "side_2d_kinematics"
    assert rec.source_revision == 1
    assert rec.schema_version == "swim-side-kinematics.v1"


def test_get_metrics_filtered_by_calculator(client, auth_headers, db_session, test_session_video):
    ann = _seed_annotation(db_session, test_session_video)
    for calc in ("side_view_metrics", "side_2d_kinematics"):
        r = client.post(
            f"/api/v1/normalized-annotations/{ann.id}/calculate-metrics"
            f"?persist=true&calculator={calc}",
            headers=auth_headers,
        )
        assert r.status_code == 200, r.text

    r_default = client.get(
        f"/api/v1/normalized-annotations/{ann.id}/metrics", headers=auth_headers
    )
    assert r_default.status_code == 200
    assert r_default.json()["calculator"] == "side_view_metrics"

    r_kin = client.get(
        f"/api/v1/normalized-annotations/{ann.id}/metrics?calculator=side_2d_kinematics",
        headers=auth_headers,
    )
    assert r_kin.status_code == 200
    assert r_kin.json()["calculator"] == "side_2d_kinematics"


def test_revision_status_tri_state(client, auth_headers, db_session, test_session_video):
    ann = _seed_annotation(db_session, test_session_video, revision=1)
    r = client.post(
        f"/api/v1/normalized-annotations/{ann.id}/calculate-metrics"
        f"?persist=true&calculator=side_2d_kinematics",
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["revision_status"] == "current"
    assert r.json()["source_revision"] == 1

    ann.revision = 2
    db_session.flush()
    r2 = client.get(
        f"/api/v1/normalized-annotations/{ann.id}/metrics?calculator=side_2d_kinematics",
        headers=auth_headers,
    )
    assert r2.status_code == 200
    assert r2.json()["revision_status"] == "stale"


def test_source_revision_null_readable_as_unknown(client, auth_headers, db_session, test_session_video):
    ann = _seed_annotation(db_session, test_session_video, revision=1)
    rec = AnnotationMetric(
        normalized_annotation_id=ann.id,
        session_video_id=test_session_video.id,
        schema_version="swim-side-kinematics.v1",
        camera_view="side",
        metrics={"summary": {}},
        quality={"level": "good"},
        calculator="side_2d_kinematics",
        calculator_version="1.0.0",
        source_revision=None,
    )
    db_session.add(rec)
    db_session.flush()

    r = client.get(
        f"/api/v1/normalized-annotations/{ann.id}/metrics?calculator=side_2d_kinematics",
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["revision_status"] == "unknown"
    assert r.json().get("source_revision") is None


def test_unsupported_calculator_returns_422(client, auth_headers, db_session, test_session_video):
    ann = _seed_annotation(db_session, test_session_video)
    r = client.post(
        f"/api/v1/normalized-annotations/{ann.id}/calculate-metrics"
        f"?calculator=does_not_exist",
        headers=auth_headers,
    )
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "unsupported_metric_calculator"


def test_legacy_side_view_metrics_regression_via_api(client, auth_headers, db_session, test_session_video):
    ann = _seed_annotation(db_session, test_session_video)
    r = client.post(
        f"/api/v1/normalized-annotations/{ann.id}/calculate-metrics?persist=true",
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["calculator"] == "side_view_metrics"
    assert r.json()["schema_version"] == "swim-side-metrics.v1"
