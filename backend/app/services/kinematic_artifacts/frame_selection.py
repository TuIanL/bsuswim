"""Frame selection for annotated keyframes.

Selection uses the exact AnnotationMetric time_series (lists of per-frame
samples). Tie-breaks: higher confidence, then earliest source frame. Head
spike and arm extension are derived from canonical frames / annotation geometry.
"""

from typing import Any

from app.services.kinematic_artifacts.frame_provider import SelectedFrame
from app.services.metrics.kinematics.frame_resolver import (
    CanonicalKinematicFrame,
    resolve_frames,
)

MAX_KEYFRAMES = 12


def _series_points(time_series: dict, key: str) -> list[dict]:
    return time_series.get(key) or []


def _pick_extremum(
    points: list[dict],
    artifact_key: str,
    formula_id: str,
    kind: str = "min",
) -> SelectedFrame | None:
    valid = [p for p in points if p.get("value") is not None]
    if not valid:
        return None

    def sort_key(p):
        value = p["value"]
        if kind == "max":
            value = -value
        return (value, -p.get("confidence", 0.0), p.get("source_video_frame") or p.get("annotation_frame") or 0)

    best = sorted(valid, key=sort_key)[0]
    return SelectedFrame(
        artifact_metric_key=artifact_key,
        annotation_frame=best["annotation_frame"],
        source_video_frame=best.get("source_video_frame"),
        selection_formula_id=formula_id,
        metadata={"value": best["value"], "selection_kind": kind},
    )


def select_angle_keyframes(time_series: dict) -> list[SelectedFrame]:
    out: list[SelectedFrame] = []
    mapping = {
        "body_posture.keyframe.body_axis_min": ("body_axis_angle_deg", "min_body_axis_angle.v1"),
        "body_posture.keyframe.body_axis_max": ("body_axis_angle_deg", "max_body_axis_angle.v1"),
        "upper_limb.keyframe.left_elbow_min": ("left_elbow_angle_deg", "min_left_elbow_angle.v1"),
        "upper_limb.keyframe.left_elbow_max": ("left_elbow_angle_deg", "max_left_elbow_angle.v1"),
        "upper_limb.keyframe.right_elbow_min": ("right_elbow_angle_deg", "min_right_elbow_angle.v1"),
        "upper_limb.keyframe.right_elbow_max": ("right_elbow_angle_deg", "max_right_elbow_angle.v1"),
        "lower_limb.keyframe.left_knee_min": ("left_knee_angle_deg", "min_left_knee_angle.v1"),
        "lower_limb.keyframe.left_knee_max": ("left_knee_angle_deg", "max_left_knee_angle.v1"),
        "lower_limb.keyframe.right_knee_min": ("right_knee_angle_deg", "min_right_knee_angle.v1"),
        "lower_limb.keyframe.right_knee_max": ("right_knee_angle_deg", "max_right_knee_angle.v1"),
    }
    for artifact_key, (metric_key, formula) in mapping.items():
        kind = "max" if artifact_key.endswith("_max") else "min"
        sel = _pick_extremum(_series_points(time_series, metric_key), artifact_key, formula, kind)
        if sel:
            out.append(sel)
    return out


def select_arm_extension_max(
    frames: list[CanonicalKinematicFrame],
    reference_body_length_px: float | None,
) -> SelectedFrame | None:
    """Select the frame with maximum per-side wrist-to-shoulder distance.

    Uses normalized distance when reference body length is available, otherwise
    falls back to raw pixel distance (same ordering within a clip, but must not
    be reported as a normalized ratio).
    """
    best: dict | None = None
    for f in frames:
        for side in ("left", "right"):
            sh = f.points.get(f"{side}_shoulder")
            wr = f.points.get(f"{side}_wrist")
            if not sh or not wr or not sh.available or not wr.available:
                continue
            dist = ((sh.x - wr.x) ** 2 + (sh.y - wr.y) ** 2) ** 0.5
            if reference_body_length_px:
                value = dist / reference_body_length_px
                basis = "normalized_distance"
            else:
                value = dist
                basis = "pixel_distance_fallback"
            if best is None or value > best["value"]:
                best = {
                    "value": value,
                    "side": side,
                    "frame": f,
                    "basis": basis,
                }
    if best is None:
        return None
    f = best["frame"]
    metadata: dict[str, Any] = {
        "value": round(best["value"], 4),
        "selected_side": best["side"],
        "selection_basis": best["basis"],
        "reference_body_length_px": reference_body_length_px,
    }
    return SelectedFrame(
        artifact_metric_key="upper_limb.keyframe.arm_extension_max",
        annotation_frame=f.annotation_frame,
        source_video_frame=f.source_video_frame,
        selection_formula_id="max_wrist_shoulder_distance_ratio.v1",
        metadata=metadata,
    )


def select_head_motion_spike(
    metric_summary: dict,
    frames: list[CanonicalKinematicFrame],
) -> SelectedFrame | None:
    """Select the detected head-motion spike with the max absolute vertical velocity.

    Falls back to N/A (None) when no spikes were detected.
    """
    envelope = metric_summary.get("head_motion_spike_frames") or {}
    candidates = envelope.get("value") if isinstance(envelope, dict) else None
    if not candidates:
        candidates = (metric_summary.get("head_motion_spike_frames") or {}).get("value")
    if not candidates:
        return None

    candidate_set = set(candidates)
    by_frame = {f.annotation_frame: f for f in frames if f.annotation_frame is not None}
    ordered = sorted(
        (f for f in frames if f.annotation_frame is not None and f.head_center.available),
        key=lambda f: f.annotation_frame,
    )
    vel: dict[int, float] = {}
    for prev, cur in zip(ordered, ordered[1:]):
        if cur.annotation_frame in candidate_set and prev.head_center.y is not None and cur.head_center.y is not None:
            vel[cur.annotation_frame] = abs(cur.head_center.y - prev.head_center.y)
    if not vel:
        return None
    best_af = max(vel, key=lambda af: (vel[af], -(by_frame[af].source_video_frame or af)))
    f = by_frame[best_af]
    return SelectedFrame(
        artifact_metric_key="head_trunk.keyframe.head_motion_spike",
        annotation_frame=best_af,
        source_video_frame=f.source_video_frame,
        selection_formula_id="max_abs_head_vertical_velocity_among_detected_spikes.v1",
        metadata={
            "spike_velocity_px": round(vel[best_af], 3),
            "detected_spike_count": len(candidates),
        },
    )


def select_all_keyframes(
    metric_summary: dict,
    time_series: dict,
    frames: list[CanonicalKinematicFrame],
    reference_body_length_px: float | None,
) -> list[SelectedFrame]:
    out = select_angle_keyframes(time_series)
    arm = select_arm_extension_max(frames, reference_body_length_px)
    if arm:
        out.append(arm)
    head = select_head_motion_spike(metric_summary, frames)
    if head:
        out.append(head)
    return out[:MAX_KEYFRAMES]
