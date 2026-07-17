"""确定性合成运动学序列生成器（纯 Python，无第三方依赖）。

用于 side_2d_kinematics 计算器的引擎层测试：

- ``build_synthetic_annotation``：≥96 帧，包含双侧 / 单侧 / 遮挡 / 估计 / 缺失
  多种可见性，且左右踝 y 含已知周期（默认 20 帧）与已知相位 lag（默认右滞后 4 帧）。
- ``build_golden_annotation``：40–80 帧双侧 COCO17 黄金 fixture，含可见性与帧映射元数据。

坐标用确定性数学生成（固定 seed 即三角函数值），保证可复现。
"""

import json
import math
import os

FPS = 60.0

COCO17 = [
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle",
]

# 基础姿态（像素），左右对称偏移
BASE_POSE = {
    "nose": (500, 270),
    "left_eye": (492, 274), "right_eye": (508, 274),
    "left_ear": (486, 278), "right_ear": (514, 278),
    "left_shoulder": (482, 300), "right_shoulder": (518, 300),
    "left_elbow": (452, 312), "right_elbow": (548, 312),
    "left_wrist": (430, 304), "right_wrist": (570, 304),
    "left_hip": (488, 360), "right_hip": (512, 360),
    "left_knee": (482, 420), "right_knee": (518, 420),
    "left_ankle": (476, 480), "right_ankle": (524, 480),
}

# 参与踢腿正弦运动的锚点（y 方向）
KICK_POINTS = ["left_ankle", "right_ankle", "left_knee", "right_knee"]


def _point(x, y, visibility="visible", confidence=1.0):
    return {"x": round(x, 2), "y": round(y, 2), "visibility": visibility, "confidence": confidence}


def _visibility_for(name, i):
    """按帧索引决定某点的可见性，覆盖多种退化情况。"""
    side = "left" if name.startswith("left") else ("right" if name.startswith("right") else None)
    # 右单侧缺失
    if i % 17 == 0 and side == "right":
        return "missing"
    # 左单侧缺失
    if i % 19 == 0 and side == "left":
        return "missing"
    # 右遮挡
    if i % 23 == 0 and side == "right":
        return "occluded"
    # 左估计
    if i % 29 == 0 and side == "left":
        return "estimated"
    return "visible"


def build_synthetic_annotation(frames: int = 96, period: int = 20, lag: int = 8) -> dict:
    """生成合成 normalized annotation（含已知周期与 lag）。

    ``lag`` 默认 8 帧，落在 freestyle 的 lag_range=(6,30) 内，便于左右踢腿时序测试。
    """
    # 头部轻微上下浮动（与踢腿同周期、相位偏移），让 head_body_synchrony 有信号
    HEAD_POINTS = ("nose", "left_eye", "right_eye", "left_ear", "right_ear")

    keypoint_frames = []
    for i in range(frames):
        t = i / FPS
        phase_l = 2 * math.pi * i / period
        # 右滞后 left 共 lag 帧 → 右相位延迟
        phase_r = 2 * math.pi * (i - lag) / period
        amp = 18.0
        head_amp = 6.0
        # 躯干中点（肩/髋）整体随踢腿轻微起伏
        trunk_bob = 3.0 * math.sin(phase_l + math.pi / 4)
        points = {}
        for name in COCO17:
            bx, by = BASE_POSE[name]
            x, y = bx, by
            if name in KICK_POINTS:
                if name.startswith("left"):
                    y = by + amp * math.sin(phase_l)
                else:
                    y = by + amp * math.sin(phase_r)
            elif name in HEAD_POINTS:
                y = by + head_amp * math.sin(phase_l + math.pi / 2)
            # 肩/髋随躯干整体浮动
            if name in ("left_shoulder", "right_shoulder", "left_hip", "right_hip"):
                y = y + trunk_bob
            vis = _visibility_for(name, i)
            conf = {"visible": 1.0, "occluded": 0.7, "estimated": 0.5, "missing": 0.0}[vis]
            if vis == "missing":
                points[name] = {"x": None, "y": None, "visibility": "missing", "confidence": 0.0}
            else:
                points[name] = _point(x, y, visibility=vis, confidence=conf)
        keypoint_frames.append({
            "frame": i,
            "annotation_frame": i,
            "source_video_frame": i,
            "time_sec": round(t, 3),
            "points": points,
        })
    return {
        "fps": FPS,
        "scale": {"method": "lane_marker", "pixels_per_meter": 840.5, "reference_length_m": 2.5},
        "swim_direction": "left_to_right",
        "reference_lines": {"waterline": {"points": [[100, 220], [1600, 220]], "confidence": 1.0}},
        "distance_markers": None,
        "events": [],
        "keypoint_frames": keypoint_frames,
        "annotation_metadata": {"stroke_type": "freestyle"},
    }


def build_golden_annotation(frames: int = 50, verified: bool = True) -> dict:
    """生成 40–80 帧双侧 COCO17 黄金 fixture（含可见性与帧映射元数据）。"""
    assert 40 <= frames <= 80
    HEAD_POINTS = ("nose", "left_eye", "right_eye", "left_ear", "right_ear")
    keypoint_frames = []
    for i in range(frames):
        t = i / FPS
        phase_l = 2 * math.pi * i / 20.0
        phase_r = 2 * math.pi * (i - 8) / 20.0
        amp = 16.0
        head_amp = 6.0
        trunk_bob = 3.0 * math.sin(phase_l + math.pi / 4)
        points = {}
        for name in COCO17:
            bx, by = BASE_POSE[name]
            x, y = bx, by
            if name in KICK_POINTS:
                y = by + amp * (math.sin(phase_l) if name.startswith("left") else math.sin(phase_r))
            elif name in HEAD_POINTS:
                y = by + head_amp * math.sin(phase_l + math.pi / 2)
            if name in ("left_shoulder", "right_shoulder", "left_hip", "right_hip"):
                y = y + trunk_bob
            points[name] = _point(x, y, visibility="visible", confidence=1.0)
        keypoint_frames.append({
            "frame": i,
            "annotation_frame": i,
            "source_video_frame": i,
            "time_sec": round(t, 3),
            "points": points,
        })
    frame_mapping = {
        "mode": "identity",
        "verified": verified,
        "verification_reason": "coco_golden_fixture",
        "source_frame_offset": 0,
        "source_frame_stride": 1,
        "entries": [{"annotation_frame": i, "source_video_frame": i} for i in range(frames)],
    }
    return {
        "fps": FPS,
        "scale": {"method": "lane_marker", "pixels_per_meter": 840.5, "reference_length_m": 2.5},
        "swim_direction": "left_to_right",
        "reference_lines": {"waterline": {"points": [[100, 220], [1600, 220]], "confidence": 1.0}},
        "distance_markers": None,
        "events": [],
        "keypoint_frames": keypoint_frames,
        "annotation_metadata": {"stroke_type": "freestyle", "frame_mapping": frame_mapping},
    }


if __name__ == "__main__":
    here = os.path.dirname(__file__)
    golden = build_golden_annotation(50, verified=True)
    out = os.path.join(here, "normalized_annotation_side_coco_golden.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(golden, fh, ensure_ascii=False, indent=2)
    print(f"wrote {out} ({len(golden['keypoint_frames'])} frames)")
