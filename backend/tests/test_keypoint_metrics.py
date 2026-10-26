"""keypoint-accuracy-benchmark 指标单元测试（tasks 5.1–5.9）。"""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.keypoint_metrics import (
    icc_2_1,
    oks_joint,
    pck,
    resolve_area,
    rmse,
    score_joint,
)
from tools.keypoint_sources import (
    Point,
    align_joints,
    normalize_joint_name,
    read_cvat_xml,
    reference_body_length,
)

FIXTURE = (
    Path(__file__).resolve().parent / "fixtures" / "kinematics_golden_v1" / "source" / "annotations.xml"
)

# 身体坐标：肩中点 (500,300)，踝中点 (500,1300) → 参考体长 1000 px
BASE = {
    "nose": (500.0, 200.0),
    "left-eye": (480.0, 190.0),
    "right-eye": (520.0, 190.0),
    "left-ear": (460.0, 200.0),
    "right-ear": (540.0, 200.0),
    "left-shoulder": (450.0, 300.0),
    "right-shoulder": (550.0, 300.0),
    "left-elbow": (400.0, 400.0),
    "right-elbow": (600.0, 400.0),
    "left-wrist": (350.0, 500.0),
    "right-wrist": (650.0, 500.0),
    "left-hip": (460.0, 600.0),
    "right-hip": (540.0, 600.0),
    "left-knee": (470.0, 900.0),
    "right-knee": (530.0, 900.0),
    "left-ankle": (480.0, 1300.0),
    "right-ankle": (520.0, 1300.0),
}


def build_frames(n: int = 12, dx: float = 0.0, dy: float = 0.0, joints=None, jitter: float = 0.0):
    joints = joints or list(BASE)
    frames = {}
    for frame in range(n):
        points = {}
        for joint in joints:
            if joint in BASE:
                x, y = BASE[joint]
            else:
                x, y = 100.0, 100.0
            points[joint] = Point(x=x + dx + jitter * frame, y=y + dy + jitter * frame, visible=True)
        frames[str(frame)] = points
    return frames


def test_body_length_matches_expected():
    assert reference_body_length(build_frames()) == pytest.approx(1000.0, abs=0.01)


def test_constant_shift_produces_exact_rmse():
    """5.1：整体平移 50px，rmse_px 必须等于 50。"""
    ref = build_frames()
    cand = build_frames(dx=50.0)
    score = score_joint(ref, cand, "left-wrist", 1000.0, 1_000_000.0)
    assert score is not None
    assert score.rmse_px == pytest.approx(50.0, abs=1e-6)
    assert score.rmse_norm == pytest.approx(0.05, abs=1e-6)


def test_pck_threshold_boundary():
    """5.2：偏移 0.03 体长只命中 0.05 与 0.10。"""
    dists = [30.0] * 10
    result = pck(dists, body_length=1000.0)
    assert result["0.02"] == 0.0
    assert result["0.05"] == 1.0
    assert result["0.10"] == 1.0


def test_pck_excludes_invisible_points():
    """5.5：任一侧不可见的帧不计入 PCK 分母。"""
    ref = build_frames(n=10)
    cand = build_frames(n=10, dx=10.0)
    for frame in range(3):
        cand[str(frame)]["left-wrist"] = Point(x=0.0, y=0.0, visible=False)
    score = score_joint(ref, cand, "left-wrist", 1000.0, 1_000_000.0)
    assert score is not None
    assert score.n == 7


def test_identical_inputs_give_icc_one():
    """5.3：完全一致 → ICC = 1.0（帧间需有变化，否则 ICC 数学上无定义）。"""
    ref = build_frames(jitter=10.0)
    score = score_joint(ref, ref, "left-elbow", 1000.0, 1_000_000.0)
    assert score is not None
    assert score.icc_x == pytest.approx(1.0, abs=1e-6)
    assert score.icc_y == pytest.approx(1.0, abs=1e-6)


def test_identical_constant_inputs_return_none_icc():
    """帧间无变化时 ICC 分母为 0 → 返回 None 而不是伪造 1.0。"""
    ref = build_frames()
    score = score_joint(ref, ref, "left-elbow", 1000.0, 1_000_000.0)
    assert score is not None
    assert score.icc is None


def test_constant_offset_lowers_icc():
    """5.4：恒定系统偏移 → ICC 明显小于 1，同时 rmse≈50。"""
    ref = build_frames(jitter=10.0)
    cand = build_frames(dx=50.0, jitter=10.0)
    score = score_joint(ref, cand, "right-knee", 1000.0, 1_000_000.0)
    assert score is not None
    assert score.rmse_px == pytest.approx(50.0, abs=1e-6)
    assert score.icc is not None
    assert score.icc < 0.95


def test_icc_degenerate_returns_none():
    assert icc_2_1([]) is None
    assert icc_2_1([(1.0, 1.0)]) is None


def test_bbox_degenerate_falls_back_to_body_length():
    """5.6：包围盒退化 → area_source=body_length_fallback。"""
    flat = {frame: {j: Point(x=0.0, y=0.0) for j in BASE} for frame in range(5)}
    area, source = resolve_area(flat, body_length=1000.0)
    assert source == "body_length_fallback"
    assert area == pytest.approx((0.5 * 1000.0) ** 2, abs=1e-6)


def test_oks_is_bounded_and_monotonic():
    area = 1_000_000.0
    assert oks_joint([0.0, 0.0], area, "left-wrist") == pytest.approx(1.0, abs=1e-9)
    assert oks_joint([100.0, 100.0], area, "left-wrist") < oks_joint([10.0, 10.0], area, "left-wrist")


def test_joint_name_normalization():
    """5.7：下划线/空格/大小写写法归一为同一关节。"""
    assert normalize_joint_name("left_shoulder") == "left-shoulder"
    assert normalize_joint_name("Left Shoulder") == "left-shoulder"
    assert normalize_joint_name("left-shoulder") == "left-shoulder"


def test_schema_alignment_skips_unmapped_joints():
    """5.8：COCO17 与 halpe26 混用 → 只评估交集，单侧关节进 skipped。"""
    ref_frames = build_frames(joints=list(BASE))
    cand_frames = build_frames(joints=list(BASE) + ["head", "neck"])

    class _Set:
        def __init__(self, frames):
            self.frames = frames

        @property
        def joints(self):
            found = set()
            for points in self.frames.values():
                found.update(points)
            return sorted(found)

    common, skipped = align_joints(_Set(ref_frames), _Set(cand_frames))
    assert "head" not in common and "neck" not in common
    assert {s["joint"] for s in skipped} == {"head", "neck"}
    assert all(s["reason"] == "missing_in_reference" for s in skipped)
    assert len(common) == 17


def test_rmse_of_empty_is_zero():
    assert rmse([]) == 0.0


def test_reference_body_length_parity_with_production():
    """5.9：与生产 compute_reference_body_length 对拍，差 ≤ 0.01 px。"""
    resolver = pytest.importorskip(
        "app.services.metrics.kinematics.frame_resolver",
        reason="需要项目依赖（pydantic/sqlalchemy）；离线环境跳过",
    )
    parsed = read_cvat_xml(FIXTURE)
    tool_value = reference_body_length(parsed.frames)

    import re

    production_input = []
    for key, points in sorted(parsed.frames.items()):
        match = re.search(r"(\d+)", key)
        production_input.append(
            {
                "annotation_frame": int(match.group(1)) if match else 0,
                "points": {
                    joint.replace("-", "_"): {
                        "x": pt.x,
                        "y": pt.y,
                        "visibility": "visible",
                    }
                    for joint, pt in points.items()
                },
            }
        )
    production_value = resolver.compute_reference_body_length(
        resolver.resolve_frames(production_input)
    ).value_px

    assert tool_value is not None and production_value is not None
    assert abs(tool_value - production_value) <= 0.01


def test_read_coco_json(tmp_path):
    """1.4：COCO keypoints 扁平数组解析为统一结构。"""
    import json

    from tools.keypoint_sources import read_coco_json

    names = list(BASE)
    keypoints = []
    for joint in names:
        x, y = BASE[joint]
        keypoints.extend([x, y, 2])
    payload = {
        "images": [{"id": 7, "file_name": "clip/frame_00000123.jpg"}],
        "annotations": [{"image_id": 7, "keypoints": keypoints}],
        "categories": [{"id": 1, "keypoints": names}],
    }
    path = tmp_path / "coco.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    parsed = read_coco_json(path)
    assert list(parsed.frames) == ["frame_00000123"]
    assert set(parsed.frames["frame_00000123"]) == set(BASE)
    assert parsed.frames["frame_00000123"]["left-shoulder"].x == pytest.approx(450.0)


def test_read_normalized_json_both_point_shapes(tmp_path):
    """1.5：归一化 JSON 的 dict 与 list 两种 points 写法都能读。"""
    import json

    from tools.keypoint_sources import read_normalized_json

    dict_form = {
        "keypoint_frames": [
            {
                "annotation_frame": 0,
                "points": {
                    "left_shoulder": {"x": 450, "y": 300, "visibility": "visible"},
                    "missing_joint": {"x": None, "y": None, "visibility": "missing"},
                },
            }
        ]
    }
    list_form = {
        "frames": [
            {
                "frame": 1,
                "points": [
                    {"name": "left_wrist", "x": 350, "y": 500},
                    {"name": "right_wrist", "x": 650, "y": 500, "visible": False},
                ],
            }
        ]
    }
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    a.write_text(json.dumps(dict_form), encoding="utf-8")
    b.write_text(json.dumps(list_form), encoding="utf-8")

    parsed_a = read_normalized_json(a)
    parsed_b = read_normalized_json(b)
    assert set(parsed_a.frames["0"]) == {"left-shoulder"}
    assert set(parsed_b.frames["1"]) == {"left-wrist"}
    assert parsed_a.skipped_points == 1
    assert parsed_b.skipped_points == 1
