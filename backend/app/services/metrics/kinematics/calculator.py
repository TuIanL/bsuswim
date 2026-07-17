"""side_2d_kinematics 计算器主入口。

把 normalized annotation 计算成 ``swim-side-kinematics.v1`` 结构的 dict，
组装四类指标 + 参考体长 + 质量评估。与旧 ``side_view_metrics`` 完全解耦。
"""

import math
from typing import Any

from app.schemas.metrics import (
    CALCULATOR_SIDE_2D_KINEMATICS,
    CALCULATOR_VERSION_SIDE_2D,
    MetricCategory,
    MetricEnvelope,
    MetricSourceInfo,
    SCHEMA_SIDE_2D_KINEMATICS,
    Side2DKinematicsResult,
)
from app.services.metrics.kinematics.body_posture import compute_body_posture
from app.services.metrics.kinematics.frame_resolver import (
    compute_reference_body_length,
    resolve_frames,
)
from app.services.metrics.kinematics.head_trunk import compute_head_trunk
from app.services.metrics.kinematics.lower_limb import compute_lower_limb
from app.services.metrics.kinematics.protocols import MetricCalculationContext
from app.services.metrics.kinematics.quality import Side2DKinematicsQualityEvaluator
from app.services.metrics.kinematics.upper_limb import compute_upper_limb


CANONICAL_KEYS: dict[str, MetricCategory] = {
    # body_posture
    "torso_axis_angle_deg": "body_posture",
    "body_axis_angle_deg": "body_posture",
    "hip_vertical_range_px": "body_posture",
    "shoulder_vertical_range_px": "body_posture",
    "body_angle_std_deg": "body_posture",
    "posture_stability_cv": "body_posture",
    # upper_limb
    "left_elbow_angle_deg": "upper_limb",
    "right_elbow_angle_deg": "upper_limb",
    "elbow_rom_deg": "upper_limb",
    "normalized_wrist_trajectory": "upper_limb",
    "arm_extension_ratio": "upper_limb",
    "wrist_velocity_px_per_frame": "upper_limb",
    # lower_limb
    "left_knee_angle_deg": "lower_limb",
    "right_knee_angle_deg": "lower_limb",
    "knee_rom_deg": "lower_limb",
    "ankle_vertical_range_px": "lower_limb",
    "kick_periodicity": "lower_limb",
    "left_right_kick_timing": "lower_limb",
    # head_trunk
    "head_vertical_range_px": "head_trunk",
    "head_shoulder_relative_offset": "head_trunk",
    "head_body_synchrony": "head_trunk",
    "head_motion_spike_frames": "head_trunk",
    "trunk_vertical_stability": "head_trunk",
}


def _ensure_canonical(summary: dict) -> dict:
    """保证每个 canonical key 都存在（task 10.8）。"""
    for key, cat in CANONICAL_KEYS.items():
        if key not in summary or summary[key] is None:
            summary[key] = MetricEnvelope(
                key=key, category=cat, value=None, availability="unavailable", confidence=0.0
            )
    return summary


def _sanitize(obj: Any) -> Any:
    """递归把 NaN/Inf 规整为 None，保证 JSON 安全（task 12.17）。"""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    return obj


class Side2DKinematicsCalculator:
    """side_2d_kinematics 计算器（符合 MetricCalculator 协议）。"""

    name = CALCULATOR_SIDE_2D_KINEMATICS
    version = CALCULATOR_VERSION_SIDE_2D
    schema_version = SCHEMA_SIDE_2D_KINEMATICS

    def calculate(self, annotation: dict, context: MetricCalculationContext) -> dict:
        keypoint_frames = annotation.get("keypoint_frames") or []
        frames = resolve_frames(keypoint_frames)
        reference_body_length = compute_reference_body_length(frames)

        fm = context.frame_mapping or (context.annotation_metadata or {}).get("frame_mapping")
        mapping_status = "verified" if (fm and fm.get("verified")) else "unknown"

        ctx = {
            "frame_mapping_status": mapping_status,
            "stroke_type": context.stroke_type,
            "frame_mapping": fm,
        }

        bp = compute_body_posture(frames, reference_body_length, ctx)
        ul = compute_upper_limb(frames, reference_body_length, ctx)
        ll = compute_lower_limb(frames, reference_body_length, ctx)
        ht = compute_head_trunk(frames, reference_body_length, ctx)

        summary: dict = {}
        time_series: dict = {}
        ranges: dict = {}
        representative_frames: dict = {}
        for mod in (bp, ul, ll, ht):
            summary.update(mod.get("summary", {}))
            time_series.update(mod.get("time_series", {}))
            ranges.update(mod.get("ranges", {}))
            representative_frames.update(mod.get("representative_frames", {}))

        summary = _ensure_canonical(summary)

        evaluator = Side2DKinematicsQualityEvaluator()
        quality = evaluator.evaluate(
            summary=summary,
            time_series=time_series,
            reference_body_length=reference_body_length,
            frames=frames,
            ctx=ctx,
        )

        source = MetricSourceInfo(
            normalized_annotation_id=context.normalized_annotation_id,
            revision=context.source_revision,
            revision_status="current",
            frame_mapping_status=mapping_status,
            stroke_type=context.stroke_type,
        )

        result = Side2DKinematicsResult(
            source=source,
            reference_body_length=reference_body_length,
            summary=summary,
            time_series=time_series,
            ranges=ranges,
            representative_frames=representative_frames,
            quality=quality,
        )
        return _sanitize(result.model_dump())
