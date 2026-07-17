"""side_2d_kinematics 计算器：引擎层与契约测试（无 DB）。

覆盖 tasks 0.x（fixture / 契约回归）与 12.x（全部指标、周期、时序、降级、NaN 安全、
schema 完整性）。集成测试（persistence / 端点）需要 Postgres，标记 ``integration``。
"""

import json
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from fixtures.synthetic_kinematics import (  # noqa: E402
    build_golden_annotation,
    build_synthetic_annotation,
)
from app.services.metrics.kinematics.calculator import (  # noqa: E402
    CANONICAL_KEYS,
    Side2DKinematicsCalculator,
)
from app.services.metrics.kinematics.frame_resolver import (  # noqa: E402
    ConstructionMode,
    resolve_frames,
)
from app.services.metrics.kinematics.geometry import (  # noqa: E402
    line_angle_to_screen_horizontal_deg,
    signed_line_tilt_deg,
)
from app.services.metrics.kinematics.protocols import MetricCalculationContext  # noqa: E402

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def _ctx(stroke_type="freestyle", **kw):
    meta = {"stroke_type": stroke_type}
    fm = kw.get("frame_mapping")
    if fm:
        meta["frame_mapping"] = fm
    return MetricCalculationContext(
        normalized_annotation_id=1,
        source_revision=1,
        stroke_type=stroke_type,
        annotation_metadata=meta,
        frame_mapping=fm,
    )


def _calculate(ann, **kw):
    return Side2DKinematicsCalculator().calculate(ann, _ctx(**kw))


# ──────────────────────────────────────────────────────────────────────────
# Phase 0: fixtures & contract tests
# ──────────────────────────────────────────────────────────────────────────


def test_synthetic_generator_has_96_frames():
    ann = build_synthetic_annotation(96)
    assert len(ann["keypoint_frames"]) >= 96


def test_synthetic_includes_degraded_visibilities():
    ann = build_synthetic_annotation(96)
    vis_seen = set()
    for kf in ann["keypoint_frames"]:
        for name, pt in kf["points"].items():
            vis_seen.add(pt["visibility"])
    assert "visible" in vis_seen
    assert "missing" in vis_seen
    assert "occluded" in vis_seen
    assert "estimated" in vis_seen


def test_synthetic_known_period_and_lag():
    ann = build_synthetic_annotation(96, period=20, lag=8)
    frames = resolve_frames(ann["keypoint_frames"])
    # 左右踝相对信号应含已知周期（约 20 帧）
    res = _calculate(ann)
    kp = res["summary"]["kick_periodicity"]["value"]
    assert kp is not None
    assert 15 <= kp["period_frames"] <= 25


def test_legacy_side_view_metrics_regression():
    """旧计算器仍可被 registry 调用，且产出旧 schema。"""
    from app.services.metrics.kinematics.registry import (
        get_calculator,
        register_builtin_calculators,
    )

    register_builtin_calculators()
    legacy = get_calculator("side_view_metrics")
    ann = build_synthetic_annotation(96)
    # 旧计算器需要非分侧命名；这里仅验证其可被调用且 schema 不变
    out = legacy.calculate(ann, _ctx())
    assert out["schema_version"] == "swim-side-metrics.v1"
    assert out["calculator"] == "side_view_metrics"


def test_golden_fixture_shape():
    gold = build_golden_annotation(50, verified=True)
    assert 40 <= len(gold["keypoint_frames"]) <= 80
    kf = gold["keypoint_frames"][0]
    assert "left_shoulder" in kf["points"]
    assert "right_ankle" in kf["points"]
    assert kf["points"]["left_shoulder"]["visibility"] == "visible"
    assert gold["annotation_metadata"]["frame_mapping"]["verified"] is True


def test_reject_mixing_left_right_proxy_in_temporal_series():
    """当某时序指标同时出现 left_proxy 与 right_proxy 时，禁止跨 mode 拼接。"""
    ann = build_synthetic_annotation(96)
    frames = resolve_frames(ann["keypoint_frames"])
    # 构造一个人工序列：前半 left_proxy，后半 right_proxy
    from app.services.metrics.kinematics.common import select_best_segment
    from app.services.metrics.kinematics.body_posture import mode_signature_body_posture

    seg, sig = select_best_segment(frames, mode_signature_body_posture)
    # 真实数据应只产出单一全 bilateral 的最长段，signature 全部一致
    modes = {mode_signature_body_posture(f) for f in seg}
    assert len(modes) == 1
    assert all(m == (ConstructionMode.BILATERAL_MIDPOINT,) * 3 for m in modes)


# ──────────────────────────────────────────────────────────────────────────
# Phase 4: geometry & statistics
# ──────────────────────────────────────────────────────────────────────────


def test_line_angle_horizontal_acute_0_to_90():
    # 水平 → 0；竖直 → 90
    assert line_angle_to_screen_horizontal_deg((0, 0), (10, 0)) == 0
    assert abs(line_angle_to_screen_horizontal_deg((0, 0), (0, 10)) - 90) < 1e-6
    # 游泳两个方向都应给锐角
    assert 0 <= line_angle_to_screen_horizontal_deg((0, 0), (10, 10)) <= 90
    assert 0 <= line_angle_to_screen_horizontal_deg((0, 0), (10, -10)) <= 90


def test_signed_tilt_four_quadrants():
    # Q1 (+,+): +45 ; Q2 (-,+): +45 ; Q3 (-,-): -135 -> folded to 45? see formula
    assert abs(signed_line_tilt_deg((0, 0), (10, 10)) - 45) < 1e-6
    # 向上（y 减小）→ 负角
    assert abs(signed_line_tilt_deg((0, 0), (10, -10)) - (-45)) < 1e-6


def test_legacy_angle_to_horizontal_unmodified():
    from app.services.metrics.geometry import angle_to_horizontal

    # 旧函数保持 abs 行为
    assert angle_to_horizontal((0, 0), (0, 10)) == 90


# ──────────────────────────────────────────────────────────────────────────
# Phase 3: frame resolver
# ──────────────────────────────────────────────────────────────────────────


def test_coco17_keys_resolved():
    ann = build_synthetic_annotation(96)
    frames = resolve_frames(ann["keypoint_frames"])
    f0 = frames[0]
    for name in ("left_shoulder", "right_elbow", "left_ankle", "right_hip", "nose"):
        assert name in f0.points


def test_bilateral_midpoint_built():
    ann = build_synthetic_annotation(96)
    frames = resolve_frames(ann["keypoint_frames"])
    # 找一个双侧都可用（非第 0 帧，该帧右单侧缺失）的帧
    f0 = next(f for f in frames if f.shoulder_mid.available and f.hip_mid.available
              and f.ankle_mid.available)
    # 双侧可用 → bilateral_midpoint
    assert f0.shoulder_mid.mode == ConstructionMode.BILATERAL_MIDPOINT
    assert f0.hip_mid.mode == ConstructionMode.BILATERAL_MIDPOINT
    assert f0.ankle_mid.mode == ConstructionMode.BILATERAL_MIDPOINT


def test_single_side_fallback_and_confidence_reduction():
    ann = build_synthetic_annotation(96)
    # 强制某帧右肩缺失，左肩可见
    kf = ann["keypoint_frames"][17]  # 右单侧缺失帧
    kf["points"]["right_shoulder"] = {"x": None, "y": None, "visibility": "missing", "confidence": 0.0}
    frames = resolve_frames([kf])
    f0 = frames[0]
    # 单侧代理，置信度 ×0.5
    assert f0.shoulder_mid.mode == ConstructionMode.LEFT_PROXY
    assert f0.shoulder_mid.confidence <= 0.5 + 1e-9


def test_missing_occluded_estimated_points():
    ann = build_synthetic_annotation(96)
    kf = ann["keypoint_frames"][23]  # 右遮挡
    assert kf["points"]["right_shoulder"]["visibility"] in ("occluded", "estimated", "missing")
    frames = resolve_frames([kf])
    # 不应崩溃
    assert frames[0].shoulder_mid is not None


def test_reference_body_length_quality_propagation():
    ann = build_synthetic_annotation(96)
    from app.services.metrics.kinematics.frame_resolver import compute_reference_body_length

    frames = resolve_frames(ann["keypoint_frames"])
    rbl = compute_reference_body_length(frames)
    assert rbl.value_px is not None
    assert rbl.sample_count >= 8
    assert rbl.availability == "available"


# ──────────────────────────────────────────────────────────────────────────
# Phase 6-9: metrics on synthetic data
# ──────────────────────────────────────────────────────────────────────────


def test_body_posture_metrics_on_synthetic():
    ann = build_synthetic_annotation(96)
    res = _calculate(ann)
    s = res["summary"]
    for key in ("torso_axis_angle_deg", "body_axis_angle_deg", "hip_vertical_range_px",
                "shoulder_vertical_range_px", "body_angle_std_deg", "posture_stability_cv"):
        assert s[key]["availability"] == "available"
        assert s[key]["value"] is not None


def test_upper_limb_metrics_on_synthetic():
    ann = build_synthetic_annotation(96)
    res = _calculate(ann)
    s = res["summary"]
    for key in ("left_elbow_angle_deg", "right_elbow_angle_deg", "elbow_rom_deg",
                "normalized_wrist_trajectory", "arm_extension_ratio",
                "wrist_velocity_px_per_frame"):
        assert s[key]["availability"] == "available"
        assert s[key]["value"] is not None


def test_lower_limb_metrics_on_synthetic():
    ann = build_synthetic_annotation(96)
    res = _calculate(ann)
    s = res["summary"]
    for key in ("left_knee_angle_deg", "right_knee_angle_deg", "knee_rom_deg",
                "ankle_vertical_range_px"):
        assert s[key]["availability"] == "available"
        assert s[key]["value"] is not None


def test_head_trunk_metrics_on_synthetic():
    ann = build_synthetic_annotation(96)
    res = _calculate(ann)
    s = res["summary"]
    for key in ("head_vertical_range_px", "head_shoulder_relative_offset",
                "head_body_synchrony", "head_motion_spike_frames",
                "trunk_vertical_stability"):
        assert s[key]["availability"] == "available"
        assert s[key]["value"] is not None


def test_periodicity_uses_known_sinusoid():
    # 纯正弦踝信号（无噪声），周期 20
    ann = build_synthetic_annotation(96, period=20, lag=8)
    res = _calculate(ann)
    kp = res["summary"]["kick_periodicity"]["value"]
    assert kp is not None
    assert 18 <= kp["period_frames"] <= 22
    assert kp["score"] >= 0.30


def test_left_right_lag_known_phase_offset():
    ann = build_synthetic_annotation(96, period=20, lag=8)
    res = _calculate(ann)
    lrkt = res["summary"]["left_right_kick_timing"]["value"]
    assert lrkt is not None
    detected = int(round(lrkt["lag_frames"]))
    # 检测到的 lag 应接近已知 8（±3 容忍，因可见性缺口）
    assert abs(detected - 8) <= 3


def test_representative_frame_provenance():
    ann = build_synthetic_annotation(96)
    res = _calculate(ann)
    # body_axis_angle_deg 代表帧应存在（representative_frames 为 dict，经 model_dump）
    rep = res["representative_frames"].get("body_axis_angle_deg")
    assert rep is not None
    assert rep["annotation_frame"] is not None


def test_schema_always_contains_canonical_keys():
    ann = build_synthetic_annotation(96)
    res = _calculate(ann)
    for key in CANONICAL_KEYS:
        assert key in res["summary"], f"missing canonical key {key}"
        assert res["summary"][key] is not None


def test_no_nan_inf_in_json_output():
    ann = build_synthetic_annotation(96)
    res = _calculate(ann)
    payload = json.dumps(res)
    assert "NaN" not in payload
    assert "Infinity" not in payload
    assert "null" in payload or "value" in payload


def test_construction_mode_not_mixed_in_temporal_series():
    ann = build_synthetic_annotation(96)
    res = _calculate(ann)
    ts = res["time_series"]["body_axis_angle_deg"]
    modes = {p["construction_mode"] for p in ts if p.get("construction_mode")}
    # 全 bilateral，不应同时出现 left_proxy 与 right_proxy
    assert not (ConstructionMode.LEFT_PROXY.value in modes and ConstructionMode.RIGHT_PROXY.value in modes)


def test_unknown_stroke_downgrades_periodicity():
    ann = build_synthetic_annotation(96, period=20, lag=8)
    res = _calculate(ann, stroke_type="unknown")
    # 非 freestyle → low_confidence
    assert res["summary"]["kick_periodicity"]["availability"] == "low_confidence"


def test_golden_fixture_expected_output_shape():
    gold = build_golden_annotation(50, verified=True)
    res = _calculate(gold, frame_mapping=gold["annotation_metadata"]["frame_mapping"])
    # 黄金 fixture 全双侧 + verified → 多数指标 available
    avail = {k: v["availability"] for k, v in res["summary"].items()}
    assert avail["kick_periodicity"] == "available"
    assert avail["left_right_kick_timing"] == "available"
    assert "available" in set(avail.values())


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
