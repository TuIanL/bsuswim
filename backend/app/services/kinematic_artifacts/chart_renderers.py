"""Matplotlib-based chart renderers (SVG output, Agg backend)."""

import math
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import numpy as np

from app.services.kinematic_artifacts.constants import (
    CHART_WIDTH,
    CHART_HEIGHT,
    RADAR_SIZE,
)

CSS_PX = "px"

_LABELS = {
    "torso_axis_angle_deg": "躯干轴角",
    "body_axis_angle_deg": "身体轴角",
    "left_elbow_angle_deg": "左肘角度",
    "right_elbow_angle_deg": "右肘角度",
    "left_knee_angle_deg": "左膝角度",
    "right_knee_angle_deg": "右膝角度",
    "left_wrist": "左腕轨迹",
    "right_wrist": "右腕轨迹",
    "left_knee": "左膝轨迹",
    "right_knee": "右膝轨迹",
    "hip": "髋部轨迹",
    "body_posture": "身体姿态",
    "upper_limb": "上肢动作",
    "lower_limb_rhythm": "下肢节奏",
    "head_trunk": "头躯干控制",
    "head_control": "头部与躯干控制",
    "data_completeness": "数据完整性",
    "posture_stability": "姿态稳定性",
    "kick_periodicity": "打腿周期性",
    "trunk_vertical_stability": "躯干垂直稳定性",
}


def _label(value: str) -> str:
    return _LABELS.get(value, value)

# Deterministic, font-agnostic style.
plt.rcParams.update(
    {
        "font.size": 11,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "figure.dpi": 100,
        "font.sans-serif": ["Hiragino Sans GB", "PingFang SC", "Microsoft YaHei", "DejaVu Sans"],
        "axes.unicode_minus": False,
    }
)


def _save_svg(fig) -> bytes:
    import io

    buf = io.BytesIO()
    fig.savefig(buf, format="svg", bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def render_angle_timeseries(
    series: dict[str, list[dict]],
    *,
    title: str = "关节角度时序",
    viewbox_w: int = CHART_WIDTH,
    viewbox_h: int = CHART_HEIGHT,
) -> bytes:
    fig, ax = plt.subplots(figsize=(viewbox_w / 100.0, viewbox_h / 100.0))
    for key, points in series.items():
        xs, ys = [], []
        for p in points:
            if p.get("value") is None:
                continue
            xs.append(p.get("source_video_frame") or p.get("annotation_frame") or p.get("frame"))
            ys.append(p["value"])
        if xs:
            ax.plot(xs, ys, label=_label(key), marker=".")
    ax.set_xlabel("视频帧")
    ax.set_ylabel("角度（°）")
    ax.set_title(title)
    ax.legend(fontsize=8)
    fig.set_layout_engine("tight")
    return _save_svg(fig)


def _body_relative(points_frame: list[dict], anchor_frame: list[dict], anchor_key: str):
    """points_frame/anchor_frame: lists of {annotation_frame, x, y}. Returns relative coords."""
    anchor_idx = {p["annotation_frame"]: p for p in anchor_frame if p.get("x") is not None}
    out = []
    for p in points_frame:
        a = anchor_idx.get(p["annotation_frame"])
        if a is None or p.get("x") is None:
            out.append((p["annotation_frame"], None, None))
        else:
            out.append((p["annotation_frame"], p["x"] - a["x"], -(p["y"] - a["y"])))  # y up positive
    return out


def render_trajectory_chart(
    trajectories: dict[str, list[tuple[int, float | None, float | None]]],
    *,
    title: str = "关节相对轨迹",
    unit: str = "body length ratio",
    viewbox_w: int = CHART_WIDTH,
    viewbox_h: int = CHART_HEIGHT,
) -> bytes:
    fig, ax = plt.subplots(figsize=(viewbox_w / 100.0, viewbox_h / 100.0))
    plotted = False
    for label, pts in trajectories.items():
        xs, ys = [], []
        for _af, rx, ry in pts:
            if rx is None or ry is None:
                continue
            xs.append(rx)
            ys.append(ry)
        if xs:
            plotted = True
            ax.plot(xs, ys, marker=".", label=_label(label))
    unit_label = "身体长度比" if unit == "body length ratio" else unit
    ax.set_xlabel(f"相对水平位置（{unit_label}）")
    ax.set_ylabel(f"相对垂直位置（{unit_label}，向上为正）")
    ax.set_title(title)
    if plotted:
        ax.legend(fontsize=8)
    else:
        ax.text(0.5, 0.5, "当前标注没有足够的位置点，无法绘制轨迹", ha="center", va="center", transform=ax.transAxes, color="#6b7280")
    ax.set_aspect("equal", adjustable="datalim")
    fig.set_layout_engine("tight")
    return _save_svg(fig)


def render_range_comparison(
    panels: dict[str, dict[str, float]],
    *,
    viewbox_w: int = CHART_WIDTH,
    viewbox_h: int = CHART_HEIGHT,
) -> bytes:
    """panels: {'Joint ROM (deg)': {label: value}, 'Vertical excursion': {...}, 'Body axis range (deg)': {...}}"""
    keys = list(panels.keys())
    fig, axes = plt.subplots(1, len(keys), figsize=(viewbox_w / 100.0, viewbox_h / 100.0))
    if len(keys) == 1:
        axes = [axes]
    for ax, pkey in zip(axes, keys):
        data = panels[pkey]
        labels = list(data.keys())
        vals = [data[k] for k in labels]
        ax.bar(range(len(labels)), vals)
        ax.set_title({
            "Joint ROM (deg)": "关节活动范围（°）",
            "Vertical excursion": "垂直波动范围",
            "Body axis range (deg)": "身体轴角范围（°）",
        }.get(pkey, pkey))
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=8)
    fig.set_layout_engine("tight")
    return _save_svg(fig)


def render_stability_radar(
    axes: list[dict],
    *,
    title: str = "当前片段运动稳定性概览",
    viewbox_w: int = RADAR_SIZE,
    viewbox_h: int = RADAR_SIZE,
) -> bytes:
    """axes: list of {axis, display_value (0-100 or None), availability}"""
    n = len(axes)
    angles = [2 * math.pi * i / n for i in range(n)]
    fig, ax = plt.subplots(figsize=(viewbox_w / 100.0, viewbox_h / 100.0), subplot_kw=dict(polar=True))
    labels = [_label(a["axis"]) for a in axes]
    values = []
    available = []
    for a in axes:
        available.append(a.get("availability") == "available" or a.get("availability") == "degraded")
        values.append(a.get("display_value") if a.get("display_value") is not None else 0)
    # close the loop
    angles_c = angles + [angles[0]]
    values_c = values + [values[0]]
    fully_available = all(available)
    if fully_available:
        ax.plot(angles_c, values_c, color="tab:blue")
        ax.fill(angles_c, values_c, color="tab:blue", alpha=0.25)
    else:
        ax.plot(angles_c, values_c, color="tab:blue", linestyle="--")
    for ang, a in zip(angles, axes):
        if not (a.get("availability") == "available" or a.get("availability") == "degraded"):
            ax.text(ang, 105, "不可用", ha="center", fontsize=8, color="red")
    ax.set_xticks(angles)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylim(0, 100)
    ax.set_title(title)
    fig.set_layout_engine("tight")
    return _save_svg(fig)
