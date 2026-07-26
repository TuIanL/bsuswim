"""Stable, factual presentation metadata for diagnostic keyframes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KeyframePresentation:
    title: str
    label: str
    metric_label: str
    unit: str | None
    selection_reason: str
    caption: str


_PRESENTATIONS: dict[str, KeyframePresentation] = {
    "body_posture.keyframe.body_axis_min": KeyframePresentation(
        "身体轴角最小", "身体姿态：最小角度", "身体轴角", "°", "指标最小值帧", "基于画面水平线的身体轴几何。",
    ),
    "body_posture.keyframe.body_axis_max": KeyframePresentation(
        "身体轴角最大", "身体姿态：最大角度", "身体轴角", "°", "指标最大值帧", "基于画面水平线的身体轴几何。",
    ),
    "upper_limb.keyframe.left_elbow_min": KeyframePresentation(
        "左肘角最小", "上肢：左肘屈曲", "左肘角", "°", "左侧指标最小值帧", "基于关节几何的左肘角。",
    ),
    "upper_limb.keyframe.left_elbow_max": KeyframePresentation(
        "左肘角最大", "上肢：左肘伸展", "左肘角", "°", "左侧指标最大值帧", "基于关节几何的左肘角。",
    ),
    "upper_limb.keyframe.right_elbow_min": KeyframePresentation(
        "右肘角最小", "上肢：右肘屈曲", "右肘角", "°", "右侧指标最小值帧", "基于关节几何的右肘角。",
    ),
    "upper_limb.keyframe.right_elbow_max": KeyframePresentation(
        "右肘角最大", "上肢：右肘伸展", "右肘角", "°", "右侧指标最大值帧", "基于关节几何的右肘角。",
    ),
    "upper_limb.keyframe.arm_extension_max": KeyframePresentation(
        "手臂伸展最大", "上肢：手臂伸展", "手臂伸展比", None, "几何伸展最大值帧", "基于腕部到肩部距离的几何量。",
    ),
    "lower_limb.keyframe.left_knee_min": KeyframePresentation(
        "左膝角最小", "下肢：左膝屈曲", "左膝角", "°", "左侧指标最小值帧", "基于关节几何的左膝角。",
    ),
    "lower_limb.keyframe.left_knee_max": KeyframePresentation(
        "左膝角最大", "下肢：左膝伸展", "左膝角", "°", "左侧指标最大值帧", "基于关节几何的左膝角。",
    ),
    "lower_limb.keyframe.right_knee_min": KeyframePresentation(
        "右膝角最小", "下肢：右膝屈曲", "右膝角", "°", "右侧指标最小值帧", "基于关节几何的右膝角。",
    ),
    "lower_limb.keyframe.right_knee_max": KeyframePresentation(
        "右膝角最大", "下肢：右膝伸展", "右膝角", "°", "右侧指标最大值帧", "基于关节几何的右膝角。",
    ),
    "head_trunk.keyframe.head_motion_spike": KeyframePresentation(
        "头部运动峰值", "头躯干：头部运动", "头部垂直运动", "px/帧", "检测到的运动峰值帧", "基于相邻标注帧的头部中心垂直位移。",
    ),
}


def keyframe_presentation(key: str) -> KeyframePresentation:
    """Return stable metadata; unknown keys remain factual and readable."""
    return _PRESENTATIONS.get(
        key,
        KeyframePresentation(
            title="自动诊断关键帧",
            label="自动诊断关键帧",
            metric_label="关联指标",
            unit=None,
            selection_reason="自动选择帧",
            caption="基于当前片段的二维骨架几何。",
        ),
    )
