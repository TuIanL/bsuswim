"""下肢指标（lower_limb）。

- left/right_knee_angle_deg：髋-膝-踝关节角均值
- knee_rom_deg：P95−P05（分左右 + 合并）
- ankle_vertical_range_px：踝相对髋中点的纵向极差（分左右）
- kick_periodicity：踝相对信号的零均值自相关主周期（泳姿感知）
- left_right_kick_timing：左右踝相对信号互相关 lag（positive = 右滞后左）
"""

from statistics import mean

from app.schemas.metrics import MetricCategory
from app.services.metrics.kinematics.common import (
    make_envelope,
    make_range,
    mode_signature_lower_limb,
    select_best_segment,
    select_representative_frame,
)
from app.services.metrics.kinematics.continuity import continuity_factor_sequence
from app.services.metrics.kinematics.frame_resolver import ConstructionMode, PointSample
from app.services.metrics.kinematics.geometry import (
    _as_xy,
    angle_between_points,
    best_period_from_autocorr,
    cross_correlation_lag,
    robust_rom_p95_p05,
)

CATEGORY: MetricCategory = "lower_limb"
MIN_SAMPLES_ANGLE = 5
MIN_SAMPLES_ROM = 8
MIN_SAMPLES_RANGE = 8
MIN_PERIODICITY = 24
MIN_TIMING = 16

STROKE_PERIODICITY_PROFILES = {
    "freestyle": {"type": "alternating", "lag_range": (6, 30)},
    "backstroke": {"type": "alternating", "lag_range": (6, 30)},
    "butterfly": {"type": "synchronous", "lag_range": (6, 20)},
    "breaststroke": {"type": "asymmetric", "lag_range": (10, 40)},
    "unknown": {"type": "generic", "lag_range": (6, 40)},
}


def _xy(p: PointSample | None):
    if p is None or not p.available:
        return None
    return (p.x, p.y)


def _knee_angle(f, side: str) -> float | None:
    h = _xy(f.points.get(f"{side}_hip"))
    k = _xy(f.points.get(f"{side}_knee"))
    a = _xy(f.points.get(f"{side}_ankle"))
    if h is None or k is None or a is None:
        return None
    return angle_between_points(h, k, a)


def _relative_ankle_y(f, side: str):
    """踝相对髋中点的纵向偏移（像素，向下为正）。"""
    a = _xy(f.points.get(f"{side}_ankle"))
    if a is None or not f.hip_mid.available:
        return None
    return a[1] - f.hip_mid.y


def compute_lower_limb(frames, reference_body_length, ctx: dict) -> dict:
    mapping_status = ctx.get("frame_mapping_status", "unknown")
    stroke_type = (ctx.get("stroke_type") or "unknown") or "unknown"
    summary: dict = {}
    time_series: dict = {}
    ranges: dict = {}
    representative_frames: dict = {}

    # ── 膝角 ──
    for side in ("left", "right"):
        key = f"{side}_knee_angle_deg"
        ts: list[dict] = []
        for f in frames:
            ang = _knee_angle(f, side)
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

    # ── 膝 ROM ──
    rom: dict = {}
    for side in ("left", "right"):
        ts = time_series.get(f"{side}_knee_angle_deg", [])
        r = robust_rom_p95_p05([p["value"] for p in ts])
        rom[side] = round(r, 2) if r is not None else None
    combined = [v for v in rom.values() if v is not None]
    rom_combined = round(mean(combined), 2) if len(combined) == 2 else (combined[0] if combined else None)
    rom_total = sum(len(time_series.get(f"{s}_knee_angle_deg", [])) for s in ("left", "right"))
    summary["knee_rom_deg"] = make_envelope(
        "knee_rom_deg", CATEGORY, value=rom if any(rom.values()) else None,
        unit="deg", sample_count=rom_total, confidence=1.0,
        reference_basis="joint_geometry", min_samples=MIN_SAMPLES_ROM,
        mapping_status=mapping_status,
        details={"left": rom.get("left"), "right": rom.get("right"), "combined": rom_combined},
    )

    # ── 踝相对纵向极差 ──
    seg, _ = select_best_segment(frames, mode_signature_lower_limb)
    ankle_range: dict = {}
    ankle_ts_by_side: dict = {"left": [], "right": []}
    for side in ("left", "right"):
        rels: list[float] = []
        rts: list[dict] = []
        for f in seg:
            ry = _relative_ankle_y(f, side)
            if ry is None:
                continue
            rels.append(ry)
            rts.append({
                "frame": f.frame_index, "time_sec": f.time_sec, "value": round(ry, 2),
                "annotation_frame": f.annotation_frame, "source_video_frame": f.source_video_frame,
                "confidence": round(_side_conf(f, side), 3),
                "construction_mode": f.hip_mid.mode.value if f.hip_mid.available else None,
            })
        rng = round(max(rels) - min(rels), 2) if len(rels) >= MIN_SAMPLES_RANGE else None
        ankle_range[side] = rng
        ankle_ts_by_side[side] = rts

    lv = ankle_range.get("left")
    rv = ankle_range.get("right")
    if lv is not None and rv is not None:
        value = {"left": lv, "right": rv}
        total_samples = MIN_SAMPLES_RANGE
    elif lv is not None:
        value = {"left": lv, "right": None}
        total_samples = MIN_SAMPLES_RANGE
    elif rv is not None:
        value = {"left": None, "right": rv}
        total_samples = MIN_SAMPLES_RANGE
    else:
        value = None
        total_samples = 0

    key = "ankle_vertical_range_px"
    summary[key] = make_envelope(
        key, CATEGORY, value=value, unit="px",
        sample_count=total_samples,
        confidence=_mean_conf([p for s in ankle_ts_by_side.values() for p in s]),
        reference_basis="pixel", min_samples=MIN_SAMPLES_RANGE, mapping_status=mapping_status,
    )
    summary[key].details.setdefault("left", lv)
    summary[key].details.setdefault("right", rv)
    if value is not None:
        time_series[key] = ankle_ts_by_side["left"] + ankle_ts_by_side["right"]

    # ── 踢腿周期性与左右时序 ──
    _compute_kick_periodicity_and_timing(
        frames, summary, time_series, ranges, representative_frames,
        mapping_status, stroke_type,
    )

    return {
        "summary": summary, "time_series": time_series,
        "ranges": ranges, "representative_frames": representative_frames,
    }


def _compute_kick_periodicity_and_timing(frames, summary, time_series, ranges,
                                         representative_frames, mapping_status, stroke_type):
    # 构建左右踝相对信号（按帧顺序）
    left_rel: list[float] = []
    right_rel: list[float] = []
    for f in frames:
        lr = _relative_ankle_y(f, "left")
        rr = _relative_ankle_y(f, "right")
        left_rel.append(lr if lr is not None else float("nan"))
        right_rel.append(rr if rr is not None else float("nan"))

    # 去除 NaN 的并行序列
    def _clean(a, b):
        pa, pb = [], []
        for x, y in zip(a, b):
            if x == x and y == y:  # 非 NaN
                pa.append(x)
                pb.append(y)
        return pa, pb

    profile = STROKE_PERIODICITY_PROFILES.get(stroke_type, STROKE_PERIODICITY_PROFILES["unknown"])
    lag_range = profile["lag_range"]
    freestyle_available = stroke_type == "freestyle"

    # 周期性：优先用左踝信号
    primary = [v for v in left_rel if v == v]
    side_used = "left"
    if len(primary) < MIN_PERIODICITY:
        primary = [v for v in right_rel if v == v]
        side_used = "right"

    period_frames = None
    score = None
    if len(primary) >= MIN_PERIODICITY:
        pf, sc = best_period_from_autocorr(primary, lag_range, min_contig=MIN_PERIODICITY, peak_threshold=0.30)
        period_frames, score = pf, sc

    stroke_unknown = not freestyle_available
    if period_frames is None or score is None:
        availability_value = None
        details = {"side": side_used, "reason": "weak_or_no_peak", "period_frames": None, "score": None}
        stroke_dep = stroke_unknown
        mapping_dep = mapping_status != "verified"
        env = make_envelope(
            "kick_periodicity", CATEGORY, value=None, unit="frame",
            sample_count=len(primary), confidence=0.0,
            reference_basis="frame_sequence", min_samples=MIN_PERIODICITY,
            mapping_status=mapping_status, stroke_unknown_and_dependent=stroke_dep,
            mapping_unverified_and_timing=mapping_dep,
            details=details,
        )
    else:
        details = {"side": side_used, "period_frames": period_frames, "score": round(score, 3),
                   "stroke_profile": profile["type"]}
        env = make_envelope(
            "kick_periodicity", CATEGORY,
            value={"period_frames": period_frames, "score": round(score, 3)},
            unit="frame", sample_count=len(primary), confidence=round(min(score, 1.0), 3),
            reference_basis="frame_sequence", min_samples=MIN_PERIODICITY,
            mapping_status=mapping_status, stroke_unknown_and_dependent=stroke_unknown,
            mapping_unverified_and_timing=mapping_status != "verified",
            details=details,
        )
    summary["kick_periodicity"] = env

    # 左右时序
    lc, rc = _clean(left_rel, right_rel)
    lag = None
    corr = None
    if len(lc) >= MIN_TIMING:
        # 已知周期时把搜索锚定在 [1, period] 内，避免整周期别名假峰；
        # 否则回退到泳姿 profile 的 lag_range。
        search_range = (1, int(period_frames)) if period_frames else lag_range
        lag, corr = cross_correlation_lag(lc, rc, search_range)
    if lag is None:
        env = make_envelope(
            "left_right_kick_timing", CATEGORY, value=None, unit="frame",
            sample_count=len(lc), confidence=0.0,
            reference_basis="frame_sequence", min_samples=MIN_TIMING,
            mapping_status=mapping_status, mapping_unverified_and_timing=mapping_status != "verified",
            details={"reason": "insufficient_or_no_lag"},
        )
    else:
        phase_offset = None
        if period_frames:
            phase_offset = round(lag / period_frames * 360.0, 1) if period_frames else None
        env = make_envelope(
            "left_right_kick_timing", CATEGORY,
            value={"lag_frames": lag, "phase_offset_deg": phase_offset},
            unit="frame", sample_count=len(lc), confidence=round(min(abs(corr or 0), 1.0), 3),
            reference_basis="frame_sequence", min_samples=MIN_TIMING,
            mapping_status=mapping_status, mapping_unverified_and_timing=mapping_status != "verified",
            details={"lag_frames": lag, "correlation": round(corr, 3) if corr is not None else None,
                     "phase_offset_deg": phase_offset},
        )
    summary["left_right_kick_timing"] = env


def _single_side(f, side: str) -> bool:
    other = "right" if side == "left" else "left"
    return (
        (f.points.get(f"{side}_hip") and f.points.get(f"{side}_hip").available)
        and not (f.points.get(f"{other}_hip") and f.points.get(f"{other}_hip").available)
    )


def _side_conf(f, side: str) -> float:
    p = f.points.get(f"{side}_hip")
    return p.confidence if (p and p.available) else 0.0


def _mean_conf(ts: list[dict]) -> float:
    confs = [p["confidence"] for p in ts if p.get("confidence")]
    return round(mean(confs), 3) if confs else 0.0
