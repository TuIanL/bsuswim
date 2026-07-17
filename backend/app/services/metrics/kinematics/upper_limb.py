"""上肢指标（upper_limb）。

- left/right_elbow_angle_deg：肩-肘-腕关节角均值
- elbow_rom_deg：P95−P05（分左右 + 合并）
- normalized_wrist_trajectory / arm_extension_ratio：腕相对肩距离 / 参考体长
- wrist_velocity_px_per_frame：腕位置逐帧差分速度
单侧缺失时正确降级（task 7.8）。
"""

from statistics import mean

from app.schemas.metrics import MetricCategory
from app.services.metrics.kinematics.common import (
    make_envelope,
    make_range,
    select_representative_frame,
)
from app.services.metrics.kinematics.continuity import (
    continuity_factor_delta,
    expected_frame_step,
)
from app.services.metrics.kinematics.frame_resolver import ConstructionMode, PointSample
from app.services.metrics.kinematics.geometry import (
    _as_xy,
    angle_between_points,
    distance_px,
    robust_rom_p95_p05,
)

CATEGORY: MetricCategory = "upper_limb"
MIN_SAMPLES_ANGLE = 5
MIN_SAMPLES_ROM = 8
MIN_SAMPLES_VEL = 6


def _xy(p: PointSample | None):
    if p is None or not p.available:
        return None
    return (p.x, p.y)


def _elbow_angle(f, side: str) -> float | None:
    s = _xy(f.points.get(f"{side}_shoulder"))
    e = _xy(f.points.get(f"{side}_elbow"))
    w = _xy(f.points.get(f"{side}_wrist"))
    if s is None or e is None or w is None:
        return None
    return angle_between_points(s, e, w)


def compute_upper_limb(frames, reference_body_length, ctx: dict) -> dict:
    mapping_status = ctx.get("frame_mapping_status", "unknown")
    frame_mapping = ctx.get("frame_mapping")
    summary: dict = {}
    time_series: dict = {}
    ranges: dict = {}
    representative_frames: dict = {}

    ref_val = reference_body_length.value_px if reference_body_length else None
    ref_low = reference_body_length is not None and reference_body_length.availability == "low_confidence"
    ref_unavailable = ref_val is None

    for side in ("left", "right"):
        key = f"{side}_elbow_angle_deg"
        ts: list[dict] = []
        for f in frames:
            ang = _elbow_angle(f, side)
            if ang is None:
                continue
            ts.append({
                "frame": f.frame_index, "time_sec": f.time_sec, "value": round(ang, 2),
                "annotation_frame": f.annotation_frame, "source_video_frame": f.source_video_frame,
                "confidence": round(_side_conf(f, side), 3),
                "construction_mode": "unilateral" if _single_side(f, side) else "bilateral_midpoint",
            })
        vals = [p["value"] for p in ts]
        summary[key] = make_envelope(
            key, CATEGORY, value=round(mean(vals), 2) if vals else None, unit="deg",
            sample_count=len(vals), confidence=_mean_conf(ts),
            reference_basis="joint_geometry", min_samples=MIN_SAMPLES_ANGLE,
            mapping_status=mapping_status,
        )
        time_series[key] = ts
        ranges[key] = make_range(key, CATEGORY, vals)
        representative_frames[key] = select_representative_frame(
            ts, key, mapping_status=mapping_status, choose="median"
        )

    # ── elbow ROM（P95−P05）──
    rom: dict = {}
    for side in ("left", "right"):
        ts = time_series.get(f"{side}_elbow_angle_deg", [])
        r = robust_rom_p95_p05([p["value"] for p in ts])
        rom[side] = round(r, 2) if r is not None else None
    combined = [v for v in rom.values() if v is not None]
    rom_combined = round(mean(combined), 2) if len(combined) == 2 else (combined[0] if combined else None)
    rom_total_samples = sum(len(time_series.get(f"{s}_elbow_angle_deg", [])) for s in ("left", "right"))
    summary["elbow_rom_deg"] = make_envelope(
        "elbow_rom_deg", CATEGORY, value=rom if any(rom.values()) else None,
        unit="deg", sample_count=rom_total_samples, confidence=_mean_conf_all(frames),
        reference_basis="joint_geometry", min_samples=MIN_SAMPLES_ROM,
        mapping_status=mapping_status,
        details={"left": rom.get("left"), "right": rom.get("right"), "combined": rom_combined},
    )

    # ── normalized wrist trajectory / arm extension ratio ──
    norm_ts: dict[str, list[dict]] = {"left": [], "right": []}
    for side in ("left", "right"):
        for f in frames:
            w = _xy(f.points.get(f"{side}_wrist"))
            sh = _xy(f.points.get(f"{side}_shoulder"))
            if w is None or sh is None:
                continue
            dist = distance_px(w, sh)
            if dist is None or ref_unavailable or ref_val in (0, None):
                continue
            norm = dist / ref_val
            norm_ts[side].append({
                "frame": f.frame_index, "time_sec": f.time_sec, "value": round(norm, 4),
                "annotation_frame": f.annotation_frame, "source_video_frame": f.source_video_frame,
                "confidence": round(_side_conf(f, side), 3),
                "construction_mode": "unilateral" if _single_side(f, side) else "bilateral_midpoint",
            })
    # 合并两侧用于 summary（取均值跨两侧）
    all_norm: list[dict] = norm_ts["left"] + norm_ts["right"]
    norm_vals = [p["value"] for p in all_norm]
    summary["normalized_wrist_trajectory"] = make_envelope(
        "normalized_wrist_trajectory", CATEGORY, value=round(mean(norm_vals), 4) if norm_vals else None,
        unit="ratio", sample_count=len(norm_vals), confidence=_mean_conf(all_norm),
        reference_basis="normalized_body_length", min_samples=MIN_SAMPLES_ANGLE,
        mapping_status=mapping_status, reference_low=ref_low,
    )
    summary["arm_extension_ratio"] = make_envelope(
        "arm_extension_ratio", CATEGORY, value=round(mean(norm_vals), 4) if norm_vals else None,
        unit="ratio", sample_count=len(norm_vals), confidence=_mean_conf(all_norm),
        reference_basis="normalized_body_length", min_samples=MIN_SAMPLES_ANGLE,
        mapping_status=mapping_status, reference_low=ref_low,
    )
    time_series["normalized_wrist_trajectory"] = all_norm

    # ── wrist velocity（逐帧差分）──
    _compute_wrist_velocity(frames, summary, time_series, ranges, representative_frames,
                            mapping_status, frame_mapping)

    return {
        "summary": summary, "time_series": time_series,
        "ranges": ranges, "representative_frames": representative_frames,
    }


def _compute_wrist_velocity(frames, summary, time_series, ranges, representative_frames,
                            mapping_status, frame_mapping):
    expected_step = expected_frame_step(frame_mapping)
    frame_basis = "source_video_frame" if mapping_status == "verified" else "annotation_frame"
    for side in ("left", "right"):
        wts: list[dict] = []
        prev = None
        prev_frame_no = None
        valid_deltas = 0
        for f in frames:
            w = _xy(f.points.get(f"{side}_wrist"))
            if w is None:
                prev = None
                continue
            if prev is None:
                prev = w
                prev_frame_no = _frame_no(f, frame_basis)
                continue
            cur_no = _frame_no(f, frame_basis)
            step = (cur_no - prev_frame_no) if (cur_no is not None and prev_frame_no is not None) else expected_step
            if step and step > 0:
                vel = distance_px(prev, w) / step
                wts.append({
                    "frame": f.frame_index, "time_sec": f.time_sec, "value": round(vel, 3),
                    "annotation_frame": f.annotation_frame, "source_video_frame": f.source_video_frame,
                    "confidence": round(_side_conf(f, side), 3),
                    "construction_mode": "unilateral" if _single_side(f, side) else "bilateral_midpoint",
                })
                valid_deltas += 1
            prev = w
            prev_frame_no = cur_no
        vals = [p["value"] for p in wts]
        key = f"wrist_velocity_px_per_frame"
        # 只取左侧或右侧（优先双侧都算会导致重复 key）；合并为单一序列
        if summary.get(key) is None or not summary[key].sample_count:
            cont = continuity_factor_delta(valid_deltas, max(len(wts), 1))
            env = make_envelope(
                key, CATEGORY, value=round(mean(vals), 3) if vals else None, unit="px/frame",
                sample_count=len(vals), confidence=_mean_conf(wts),
                reference_basis="pixel", min_samples=MIN_SAMPLES_VEL,
                mapping_status=mapping_status, continuity_factor=cont,
                frame_basis=frame_basis,
                details={"frame_basis": frame_basis, "expected_step": expected_step,
                         "actual_delta_count": len(wts), "side": side},
            )
            summary[key] = env
            time_series[key] = wts
            ranges[key] = make_range(key, CATEGORY, vals)
            representative_frames[key] = select_representative_frame(
                wts, key, mapping_status=mapping_status, choose="median"
            )
        else:
            # 两侧都算：把右侧并入左侧序列（不覆盖）
            existing = time_series.get(key, [])
            existing.extend(wts)
            time_series[key] = existing
            new_vals = [p["value"] for p in existing]
            summary[key].sample_count = len(new_vals)
            summary[key].value = round(mean(new_vals), 3) if new_vals else None
            ranges[key] = make_range(key, CATEGORY, new_vals)


def _frame_no(f, basis: str):
    if basis == "source_video_frame":
        return f.source_video_frame
    return f.annotation_frame if f.annotation_frame is not None else f.frame_index


def _single_side(f, side: str) -> bool:
    other = "right" if side == "left" else "left"
    return (
        (f.points.get(f"{side}_shoulder") and f.points.get(f"{side}_shoulder").available)
        and not (f.points.get(f"{other}_shoulder") and f.points.get(f"{other}_shoulder").available)
    )


def _side_conf(f, side: str) -> float:
    p = f.points.get(f"{side}_shoulder")
    return p.confidence if (p and p.available) else 0.0


def _mean_conf(ts: list[dict]) -> float:
    confs = [p["confidence"] for p in ts if p.get("confidence")]
    return round(mean(confs), 3) if confs else 0.0


def _mean_conf_all(frames) -> float:
    return 1.0 if frames else 0.0
