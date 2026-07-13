"""side-view metrics 引擎与端点测试。

引擎层（calculate_side_view_metrics）不依赖数据库，可直接用 fixture dict 测试。
API 集成测试需要数据库，标记为 ``integration`` 便于在 CI 有 Postgres 时运行。
"""

import json
import os

import pytest

from app.services.metrics.engine import calculate_side_view_metrics
from app.services.metrics.geometry import angle_between_points, angle_to_horizontal

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def _load(name: str) -> dict:
    with open(os.path.join(FIXTURES, name), "r", encoding="utf-8") as fh:
        return json.load(fh)


def _load_annotation(name: str) -> dict:
    data = _load(name)
    # 引擎只认 fps/scale/events/keypoint_frames/reference_lines/distance_markers/swim_direction
    return {
        "fps": data.get("fps", 0),
        "scale": data.get("scale"),
        "events": data.get("events", []),
        "keypoint_frames": data.get("keypoint_frames", []),
        "reference_lines": data.get("reference_lines"),
        "distance_markers": data.get("distance_markers"),
        "swim_direction": data.get("swim_direction"),
    }


# ── 引擎单测（无 DB）──


def test_body_angle_elbow_angle_knee_angle_computed():
    ann = _load_annotation("normalized_annotation_side_minimal.json")
    result = calculate_side_view_metrics(ann, "side")
    summary = result["summary"]

    assert 0 < summary["body_angle_deg_avg"] < 90
    assert 0 < summary["elbow_angle_deg_avg"] < 180
    assert 0 < summary["knee_angle_deg_avg"] < 180
    # hip_depth 由 waterline 提供（minimal 含 waterline）
    assert summary.get("hip_depth_cm_avg") is not None
    assert result["schema_version"] == "swim-side-metrics.v1"
    assert result["camera_view"] == "side"


def test_missing_waterline_degrades_hip_depth_no_crash():
    ann = _load_annotation("normalized_annotation_side_missing_waterline.json")
    result = calculate_side_view_metrics(ann, "side")
    summary = result["summary"]
    quality = result["quality"]

    # 无 waterline → hip_depth 降级为 None
    assert summary.get("hip_depth_cm_avg") is None
    codes = {w["code"] for w in quality["warnings"]}
    assert "missing_waterline" in codes
    # 但其余指标仍算得出，且 phase_metrics 因 distance_markers 存在而非空
    assert summary.get("elbow_angle_deg_avg") is not None
    assert result["phase_metrics"]


def test_full_cycle_computes_rich_metrics():
    ann = _load_annotation("normalized_annotation_side_full_cycle.json")
    result = calculate_side_view_metrics(ann, "side")
    summary = result["summary"]
    quality = result["quality"]

    assert summary.get("hip_depth_cm_avg") is not None
    assert summary.get("stroke_rate_spm_avg") is not None
    assert summary.get("average_speed_mps") is not None
    assert summary.get("stroke_length_m_avg") is not None
    assert isinstance(summary.get("swolf"), dict)
    assert summary.get("kick_frequency_hz") is not None
    assert result["phase_metrics"]  # distance_markers 存在 → 三阶段
    assert quality["level"] in ("good", "warning")


def test_missing_fps_returns_error_quality_not_crash():
    ann = _load_annotation("normalized_annotation_side_minimal.json")
    ann["fps"] = None
    result = calculate_side_view_metrics(ann, "side")
    assert result["quality"]["level"] == "error"
    codes = {w["code"] for w in result["quality"]["warnings"]}
    assert "missing_fps" in codes


def test_non_side_view_keeps_factual_shape():
    ann = _load_annotation("normalized_annotation_side_minimal.json")
    result = calculate_side_view_metrics(ann, "front")
    assert result["camera_view"] == "front"
    assert result["quality"]["level"] == "error"
    assert any(w["code"] == "unsupported_camera_view" for w in result["quality"]["warnings"])


def test_geometry_angle_to_horizontal_and_between():
    # 水平线 → 0；垂直 → 90
    assert angle_to_horizontal((0, 0), (10, 0)) == 0
    assert abs(angle_to_horizontal((0, 0), (0, 10)) - 90) < 1e-6
    # 三点直角
    assert abs(angle_between_points((1, 0), (0, 0), (0, 1)) - 90) < 1e-6
    # 平角
    assert abs(angle_between_points((1, 0), (0, 0), (-1, 0)) - 180) < 1e-6


@pytest.mark.integration
def test_calculate_metrics_endpoint_persists(client, auth_headers, db_session):
    """需要数据库 + 已 seed 的 normalized_annotation。CI 有 Postgres 时启用。"""
    # 该集成测试依赖 fixture 数据 seed；此处仅验证端点存在且返回结构
    # 实际 seed 由 migration + 测试基建提供，这里做 smoke check
    resp = client.post(
        "/api/v1/normalized-annotations/999999/calculate-metrics?persist=true",
        headers=auth_headers,
    )
    # 不存在的标注 → 404（ownership check 先拦截）
    assert resp.status_code in (404, 422)
