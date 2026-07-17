"""头部与躯干控制指标（head_trunk）。

- head_vertical_range_px：头中心纵向极差
- head_shoulder_relative_offset：头相对肩偏移 / 参考体长
- head_body_synchrony：头中心与躯干中点一阶差分的 Pearson 相关
- head_motion_spike_frames：头部速度 MAD 稳健 z 尖峰帧
- trunk_vertical_stability：躯干中点去趋势残差标准差 / 参考体长
支持鼻子单点与部分头部回退（task 9.7）。
"""

from statistics import mean, pstdev

from app.schemas.metrics import MetricCategory
from app.services.metrics.kinematics.common import (
    make_envelope,
    make_range,
    select_best_segment,
    select_representative_frame,
)
from app.services.metrics.kinematics.frame_resolver import CanonicalKinematicFrame, ConstructionMode
from app.services.metrics.kinematics.geometry import (
    mad_velocity_spikes,
    pearson_correlation,
    std_dev,
)

CATEGORY: MetricCategory = "head_trunk"
MIN_SAMPLES = 8
MIN_SYNC = 12
MIN_STABILITY = 12


def _head_sig(f: CanonicalKinematicFrame):
    return (f.head_center.mode,) if f.head_center.available else None


def _trunk_sig(f: CanonicalKinematicFrame):
    return (f.trunk_mid.mode,) if f.trunk_mid.available else None


def _detrend_residual_std(ys: list[float]) -> float | None:
    n = len(ys)
    if n < 3:
        return None
    xs = list(range(n))
    mx = mean(xs)
    my = mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx < 1e-9:
        return None
    sxy = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    b1 = sxy / sxx
    b0 = my - b1 * mx
    resid = [ys[i] - (b0 + b1 * xs[i]) for i in range(n)]
    return pstdev(resid)


def compute_head_trunk(frames, reference_body_length, ctx: dict) -> dict:
    mapping_status = ctx.get("frame_mapping_status", "unknown")
    summary: dict = {}
    time_series: dict = {}
    ranges: dict = {}
    representative_frames: dict = {}

    ref_val = reference_body_length.value_px if reference_body_length else None
    ref_low = reference_body_length is not None and reference_body_length.availability == "low_confidence"
    ref_unavailable = ref_val is None

    # ── 头中心可用帧 ──
    head_seg, _ = select_best_segment(frames, _head_sig)
    head_ys: list[float] = [f.head_center.y for f in head_seg if f.head_center.y is not None]

    head_range = round(max(head_ys) - min(head_ys), 2) if len(head_ys) >= MIN_SAMPLES else None
    summary["head_vertical_range_px"] = make_envelope(
        "head_vertical_range_px", CATEGORY, value=head_range, unit="px",
        sample_count=len(head_ys), confidence=_conf(head_seg, "head"),
        reference_basis="pixel", min_samples=MIN_SAMPLES, mapping_status=mapping_status,
    )
    time_series["head_vertical_range_px"] = [
        {"frame": f.frame_index, "time_sec": f.time_sec, "value": round(f.head_center.y, 2),
         "annotation_frame": f.annotation_frame, "source_video_frame": f.source_video_frame,
         "confidence": round(f.head_center.confidence, 3) if f.head_center.available else None,
         "construction_mode": f.head_center.mode.value if f.head_center.available else None}
        for f in head_seg if f.head_center.y is not None
    ]

    # ── 头肩相对偏移（归一化）──
    offset_vals: list[float] = []
    for f in head_seg:
        if f.head_center.y is None or not f.shoulder_mid.available or ref_unavailable or ref_val in (0, None):
            continue
        off = (f.head_center.y - f.shoulder_mid.y) / ref_val
        offset_vals.append(off)
    off_mean = round(mean(offset_vals), 4) if offset_vals else None
    summary["head_shoulder_relative_offset"] = make_envelope(
        "head_shoulder_relative_offset", CATEGORY, value=off_mean, unit="ratio",
        sample_count=len(offset_vals), confidence=_conf(head_seg, "head"),
        reference_basis="normalized_body_length", min_samples=MIN_SAMPLES,
        mapping_status=mapping_status, reference_low=ref_low,
    )

    # ── 头体同步（一阶差分 Pearson）──
    sync_seg = [f for f in frames if f.head_center.available and f.trunk_mid.available]
    head_d = _first_diff([f.head_center.y for f in sync_seg])
    trunk_d = _first_diff([f.trunk_mid.y for f in sync_seg])
    sync_r = pearson_correlation(head_d, trunk_d) if len(sync_seg) >= MIN_SYNC else None
    summary["head_body_synchrony"] = make_envelope(
        "head_body_synchrony", CATEGORY,
        value=round(sync_r, 3) if sync_r is not None else None, unit="r",
        sample_count=len(sync_seg), confidence=_conf_seq(sync_seg),
        reference_basis="frame_sequence", min_samples=MIN_SYNC,
        mapping_status=mapping_status,
    )

    # ── 头部运动尖峰帧（MAD 稳健 z）──
    head_y_full = [f.head_center.y for f in frames if f.head_center.available and f.head_center.y is not None]
    spike_idx = mad_velocity_spikes(head_y_full, threshold=3.5) if len(head_y_full) >= 4 else []
    # 映射回帧
    avail_frames = [f for f in frames if f.head_center.available and f.head_center.y is not None]
    spike_frames = []
    for i in spike_idx:
        if 0 <= i + 1 < len(avail_frames):
            frm = avail_frames[i + 1]
            spike_frames.append(frm.annotation_frame if frm.annotation_frame is not None else frm.frame_index)
    summary["head_motion_spike_frames"] = make_envelope(
        "head_motion_spike_frames", CATEGORY, value=spike_frames, unit="frame",
        sample_count=len(head_y_full), confidence=_conf_seq(avail_frames),
        reference_basis="frame_sequence", min_samples=MIN_SAMPLES,
        mapping_status=mapping_status,
        details={"spike_count": len(spike_frames), "spike_annotation_frames": spike_frames},
    )

    # ── 躯干纵向稳定性（去趋势残差 / 参考体长）──
    trunk_seg, _ = select_best_segment(frames, _trunk_sig)
    trunk_ys = [f.trunk_mid.y for f in trunk_seg if f.trunk_mid.y is not None]
    res_std = _detrend_residual_std(trunk_ys) if len(trunk_ys) >= MIN_STABILITY else None
    if res_std is not None and not ref_unavailable and ref_val not in (0, None):
        stability = round(res_std / ref_val, 4)
    else:
        stability = None
    summary["trunk_vertical_stability"] = make_envelope(
        "trunk_vertical_stability", CATEGORY, value=stability, unit="ratio",
        sample_count=len(trunk_ys), confidence=_conf(trunk_seg, "trunk"),
        reference_basis="normalized_body_length", min_samples=MIN_STABILITY,
        mapping_status=mapping_status, reference_low=ref_low,
    )
    time_series["trunk_vertical_stability"] = [
        {"frame": f.frame_index, "time_sec": f.time_sec, "value": round(f.trunk_mid.y, 2),
         "annotation_frame": f.annotation_frame, "source_video_frame": f.source_video_frame,
         "confidence": round(f.trunk_mid.confidence, 3) if f.trunk_mid.available else None,
         "construction_mode": f.trunk_mid.mode.value if f.trunk_mid.available else None}
        for f in trunk_seg if f.trunk_mid.y is not None
    ]

    return {
        "summary": summary, "time_series": time_series,
        "ranges": ranges, "representative_frames": representative_frames,
    }


def _first_diff(ys: list[float]) -> list[float]:
    return [ys[i + 1] - ys[i] for i in range(len(ys) - 1)]


def _conf(seg, kind: str) -> float:
    if kind == "head":
        confs = [f.head_center.confidence for f in seg if f.head_center.available]
    else:
        confs = [f.trunk_mid.confidence for f in seg if f.trunk_mid.available]
    return round(mean(confs), 3) if confs else 0.0


def _conf_seq(frames) -> float:
    confs = []
    for f in frames:
        if f.head_center.available:
            confs.append(f.head_center.confidence)
        elif f.trunk_mid.available:
            confs.append(f.trunk_mid.confidence)
    return round(mean(confs), 3) if confs else 0.0
