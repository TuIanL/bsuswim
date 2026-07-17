"""side_2d_kinematics 指标模块共享工具。

- 统一可用性判定（design D12）
- MetricEnvelope 构造
- 按 construction_mode signature 选取最长连续段（design D6，禁止跨 mode 拼接）
"""

from statistics import mean, median, pstdev
from typing import Any, Callable

from app.schemas.metrics import (
    MetricCategory,
    MetricEnvelope,
    MetricProvenance,
    MetricRange,
    RepresentativeFrame,
)
from app.services.metrics.kinematics.frame_resolver import (
    CanonicalKinematicFrame,
    ConstructionMode,
)

CONF_LOW = 0.65
CONT_THRESHOLD = 0.70

BODY_POSTURE_SIG = (
    ConstructionMode.BILATERAL_MIDPOINT,
    ConstructionMode.BILATERAL_MIDPOINT,
    ConstructionMode.BILATERAL_MIDPOINT,
)


def compute_availability(
    *,
    value_present: bool,
    sample_count: int,
    min_samples: int,
    confidence: float,
    continuity_factor: float = 1.0,
    reference_low: bool = False,
    mapping_unverified_and_timing: bool = False,
    stroke_unknown_and_dependent: bool = False,
) -> str:
    """统一可用性判定（design D12）。"""
    if not value_present or sample_count == 0:
        return "unavailable"
    if sample_count < min_samples:
        return "low_confidence"
    if confidence < CONF_LOW:
        return "low_confidence"
    if continuity_factor < CONT_THRESHOLD:
        return "low_confidence"
    if reference_low:
        return "low_confidence"
    if mapping_unverified_and_timing:
        return "low_confidence"
    if stroke_unknown_and_dependent:
        return "low_confidence"
    return "available"


def make_envelope(
    key: str,
    category: MetricCategory,
    *,
    value: Any = None,
    unit: str | None = None,
    sample_count: int = 0,
    confidence: float = 0.0,
    reference_basis: str = "screen_horizontal",
    details: dict | None = None,
    min_samples: int = 1,
    continuity_factor: float = 1.0,
    mapping_status: str = "unknown",
    reference_low: bool = False,
    mapping_unverified_and_timing: bool = False,
    stroke_unknown_and_dependent: bool = False,
    annotation_frame_ranges: list[list[int]] | None = None,
    source_video_frame_ranges: list[list[int]] | None = None,
    frame_basis: str = "annotation_frame",
) -> MetricEnvelope:
    value_present = value is not None
    availability = compute_availability(
        value_present=value_present,
        sample_count=sample_count,
        min_samples=min_samples,
        confidence=confidence,
        continuity_factor=continuity_factor,
        reference_low=reference_low,
        mapping_unverified_and_timing=mapping_unverified_and_timing,
        stroke_unknown_and_dependent=stroke_unknown_and_dependent,
    )
    provenance = MetricProvenance(
        annotation_frame_ranges=annotation_frame_ranges or [],
        source_video_frame_ranges=source_video_frame_ranges or [],
        frame_basis=frame_basis,
        mapping_status=mapping_status,
    )
    if details is None:
        details = {}
    details.setdefault("continuity_factor", round(continuity_factor, 3))
    details.setdefault("mapping_status", mapping_status)
    return MetricEnvelope(
        key=key,
        category=category,
        value=value if value is not None else None,
        unit=unit,
        sample_count=sample_count,
        availability=availability,
        confidence=round(confidence, 3),
        provenance=provenance,
        reference_basis=reference_basis,
        details=details,
    )


def mode_signature_body_posture(f: CanonicalKinematicFrame) -> tuple | None:
    if not (f.shoulder_mid.available and f.hip_mid.available and f.ankle_mid.available):
        return None
    return (f.shoulder_mid.mode, f.hip_mid.mode, f.ankle_mid.mode)


def mode_signature_lower_limb(f: CanonicalKinematicFrame) -> tuple | None:
    if not (f.hip_mid.available and f.ankle_mid.available):
        return None
    return (f.hip_mid.mode, f.ankle_mid.mode)


def select_best_segment(
    frames: list[CanonicalKinematicFrame],
    sig_fn: Callable[[CanonicalKinematicFrame], tuple | None],
) -> tuple[list[CanonicalKinematicFrame], tuple | None]:
    """按 mode signature 分组，返回最长连续有效段（design D6）。

    优先全 bilateral 的最长连续段；否则最长连续段。
    """
    # 标注每段：连续相同 signature（非 None）为一组
    segments: list[list[CanonicalKinematicFrame]] = []
    current_sig = None
    current: list[CanonicalKinematicFrame] = []
    for f in frames:
        sig = sig_fn(f)
        if sig is None:
            if current:
                segments.append(current)
                current = []
            current_sig = None
            continue
        if sig == current_sig:
            current.append(f)
        else:
            if current:
                segments.append(current)
            current = [f]
            current_sig = sig
    if current:
        segments.append(current)

    if not segments:
        return [], None

    # 优先全 bilateral 段，否则按长度选最长
    bilateral_segs = [s for s in segments if s[0] and mode_signature_body_posture_equiv(s[0], sig_fn)]
    candidates = bilateral_segs if bilateral_segs else segments
    best = max(candidates, key=lambda s: len(s))
    return best, sig_fn(best[0]) if best else None


def mode_signature_body_posture_equiv(frame: CanonicalKinematicFrame, sig_fn) -> bool:
    sig = sig_fn(frame)
    if sig is None:
        return False
    return all(s == ConstructionMode.BILATERAL_MIDPOINT for s in sig)


def make_range(metric_key: str, category: MetricCategory, values: list[float]) -> MetricRange:
    vals = [v for v in values if v is not None]
    if not vals:
        return MetricRange(metric_key=metric_key, category=category)
    from app.services.metrics.kinematics.geometry import percentile

    return MetricRange(
        metric_key=metric_key,
        category=category,
        min=round(min(vals), 3),
        max=round(max(vals), 3),
        p05=round(percentile(vals, 5), 3),
        p95=round(percentile(vals, 95), 3),
    )


def select_representative_frame(
    series: list[dict],
    metric_key: str,
    mapping_status: str = "unknown",
    choose: str = "median",
) -> RepresentativeFrame:
    """从 time series 中选代表性帧（默认取最接近中位数的帧）。"""
    valid = [p for p in series if p.get("value") is not None]
    if not valid:
        return RepresentativeFrame(
            metric_key=metric_key,
            extractable=False,
            mapping_status=mapping_status,
            reason="no valid samples",
        )
    vals = [p["value"] for p in valid]
    target = median(vals) if choose == "median" else mean(vals)
    best = min(valid, key=lambda p: abs(p["value"] - target))
    extractable = mapping_status == "verified" and best.get("source_video_frame") is not None
    return RepresentativeFrame(
        metric_key=metric_key,
        annotation_frame=best.get("annotation_frame"),
        source_video_frame=best.get("source_video_frame"),
        time_sec=best.get("time_sec"),
        value=best.get("value"),
        extractable=extractable,
        mapping_status=mapping_status,
    )
