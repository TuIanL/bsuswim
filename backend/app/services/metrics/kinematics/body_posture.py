"""身体姿态与稳定性指标（body_posture）。

对应 canonical 定义：
- torso_axis_angle_deg / body_axis_angle_deg：肩中点→髋/踝中点连线与屏幕水平锐角
- hip_vertical_range_px / shoulder_vertical_range_px：中点 y 的极值差
- body_angle_std_deg：身体轴角序列标准差
- posture_stability_cv：100×std/|mean|（mean<1° 时降级）
"""

from statistics import mean, pstdev

from app.schemas.metrics import MetricCategory
from app.services.metrics.kinematics.common import (
    compute_availability,
    make_envelope,
    make_range,
    mode_signature_body_posture,
    select_best_segment,
    select_representative_frame,
)
from app.services.metrics.kinematics.frame_resolver import ConstructionMode
from app.services.metrics.kinematics.geometry import (
    coefficient_of_variation_pct,
    line_angle_to_screen_horizontal_deg,
    std_dev,
)

CATEGORY: MetricCategory = "body_posture"
MIN_SAMPLES = 8


def _point(f, value, mode) -> dict:
    return {
        "frame": f.frame_index,
        "time_sec": f.time_sec,
        "value": value,
        "annotation_frame": f.annotation_frame,
        "source_video_frame": f.source_video_frame,
        "confidence": round(f.shoulder_mid.confidence, 3) if f.shoulder_mid.available else None,
        "construction_mode": mode.value if mode else None,
    }


def compute_body_posture(frames, reference_body_length, ctx: dict) -> dict:
    mapping_status = ctx.get("frame_mapping_status", "unknown")
    summary: dict = {}
    time_series: dict = {}
    ranges: dict = {}
    representative_frames: dict = {}

    seg, _sig = select_best_segment(frames, mode_signature_body_posture)
    if not seg:
        for key in (
            "torso_axis_angle_deg", "body_axis_angle_deg", "hip_vertical_range_px",
            "shoulder_vertical_range_px", "body_angle_std_deg", "posture_stability_cv",
        ):
            summary[key] = make_envelope(
                key, CATEGORY, value=None, min_samples=MIN_SAMPLES,
                mapping_status=mapping_status,
            )
        return {
            "summary": summary, "time_series": time_series,
            "ranges": ranges, "representative_frames": representative_frames,
        }

    torso_ts: list[dict] = []
    body_ts: list[dict] = []
    hip_ys: list[float] = []
    shoulder_ys: list[float] = []
    for f in seg:
        ta = line_angle_to_screen_horizontal_deg(f.shoulder_mid, f.hip_mid)
        ba = line_angle_to_screen_horizontal_deg(f.shoulder_mid, f.ankle_mid)
        if ta is not None:
            torso_ts.append(_point(f, round(ta, 2), f.shoulder_mid.mode))
        if ba is not None:
            body_ts.append(_point(f, round(ba, 2), f.shoulder_mid.mode))
        if f.hip_mid.y is not None:
            hip_ys.append(f.hip_mid.y)
        if f.shoulder_mid.y is not None:
            shoulder_ys.append(f.shoulder_mid.y)

    torso_vals = [p["value"] for p in torso_ts]
    body_vals = [p["value"] for p in body_ts]

    # 均值
    torso_mean = round(mean(torso_vals), 2) if torso_vals else None
    body_mean = round(mean(body_vals), 2) if body_vals else None

    summary["torso_axis_angle_deg"] = make_envelope(
        "torso_axis_angle_deg", CATEGORY, value=torso_mean, unit="deg",
        sample_count=len(torso_vals), confidence=_seg_conf(seg),
        reference_basis="screen_horizontal", min_samples=MIN_SAMPLES,
        mapping_status=mapping_status,
    )
    summary["body_axis_angle_deg"] = make_envelope(
        "body_axis_angle_deg", CATEGORY, value=body_mean, unit="deg",
        sample_count=len(body_vals), confidence=_seg_conf(seg),
        reference_basis="screen_horizontal", min_samples=MIN_SAMPLES,
        mapping_status=mapping_status,
    )

    # 纵向极差
    hip_range = round(max(hip_ys) - min(hip_ys), 2) if len(hip_ys) >= MIN_SAMPLES else None
    shoulder_range = round(max(shoulder_ys) - min(shoulder_ys), 2) if len(shoulder_ys) >= MIN_SAMPLES else None
    summary["hip_vertical_range_px"] = make_envelope(
        "hip_vertical_range_px", CATEGORY, value=hip_range, unit="px",
        sample_count=len(hip_ys), confidence=_seg_conf(seg),
        reference_basis="pixel", min_samples=MIN_SAMPLES,
        mapping_status=mapping_status,
    )
    summary["shoulder_vertical_range_px"] = make_envelope(
        "shoulder_vertical_range_px", CATEGORY, value=shoulder_range, unit="px",
        sample_count=len(shoulder_ys), confidence=_seg_conf(seg),
        reference_basis="pixel", min_samples=MIN_SAMPLES,
        mapping_status=mapping_status,
    )

    # 序列统计
    body_std = std_dev(body_vals)
    body_std = round(body_std, 3) if body_std is not None else None
    summary["body_angle_std_deg"] = make_envelope(
        "body_angle_std_deg", CATEGORY, value=body_std, unit="deg",
        sample_count=len(body_vals), confidence=_seg_conf(seg),
        reference_basis="screen_horizontal", min_samples=MIN_SAMPLES,
        mapping_status=mapping_status,
    )

    cv = coefficient_of_variation_pct(body_vals, guard_mean_min=1.0)
    cv = round(cv, 2) if cv is not None else None
    summary["posture_stability_cv"] = make_envelope(
        "posture_stability_cv", CATEGORY, value=cv, unit="%",
        sample_count=len(body_vals), confidence=_seg_conf(seg),
        reference_basis="screen_horizontal", min_samples=MIN_SAMPLES,
        mapping_status=mapping_status,
        details={"mean_deg": body_mean, "std_deg": body_std},
    )

    time_series["torso_axis_angle_deg"] = torso_ts
    time_series["body_axis_angle_deg"] = body_ts
    ranges["torso_axis_angle_deg"] = make_range("torso_axis_angle_deg", CATEGORY, torso_vals)
    ranges["body_axis_angle_deg"] = make_range("body_axis_angle_deg", CATEGORY, body_vals)

    representative_frames["body_axis_angle_deg"] = select_representative_frame(
        body_ts, "body_axis_angle_deg", mapping_status=mapping_status, choose="median"
    )
    representative_frames["torso_axis_angle_deg"] = select_representative_frame(
        torso_ts, "torso_axis_angle_deg", mapping_status=mapping_status, choose="median"
    )

    return {
        "summary": summary, "time_series": time_series,
        "ranges": ranges, "representative_frames": representative_frames,
    }


def _seg_conf(seg) -> float:
    confs = [
        f.shoulder_mid.confidence
        for f in seg
        if f.shoulder_mid.available
    ]
    if not confs:
        return 0.0
    return round(sum(confs) / len(confs), 3)
