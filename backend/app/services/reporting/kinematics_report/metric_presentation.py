"""Metric presentation registry and envelope-to-ReportMetric projection."""

from app.schemas.kinematics_report import MetricAvailability, ReferenceBasis, ReportMetric
from app.schemas.metrics import MetricEnvelope
from .constants import REFERENCE_BASIS_LABELS

# ── Metric presentation config: label, order, decimals ──

KINEMATICS_REPORT_METRICS: dict[str, dict] = {
    # body_posture
    "torso_axis_angle_deg": {"label": "躯干轴相对画面水平角", "order": 5, "decimals": 1},
    "body_axis_angle_deg": {"label": "身体轴相对画面水平角", "order": 10, "decimals": 1},
    "hip_vertical_range_px": {"label": "髋部垂直波动范围", "order": 20, "decimals": 1},
    "shoulder_vertical_range_px": {"label": "肩部垂直波动范围", "order": 30, "decimals": 1},
    "body_angle_std_deg": {"label": "身体轴角波动标准差", "order": 40, "decimals": 1},
    "posture_stability_cv": {"label": "姿态稳定性变异系数", "order": 50, "decimals": 3},
    # upper_limb
    "left_elbow_angle_deg": {"label": "左肘关节角度", "order": 10, "decimals": 1},
    "right_elbow_angle_deg": {"label": "右肘关节角度", "order": 20, "decimals": 1},
    "elbow_rom_deg": {"label": "肘关节运动范围", "order": 30, "decimals": 1},
    "normalized_wrist_trajectory": {"label": "标准化腕部轨迹", "order": 40, "decimals": 3},
    "arm_extension_ratio": {"label": "手臂伸展比", "order": 50, "decimals": 3},
    "wrist_velocity_px_per_frame": {"label": "腕部速度", "order": 60, "decimals": 2},
    # lower_limb
    "left_knee_angle_deg": {"label": "左膝关节角度", "order": 10, "decimals": 1},
    "right_knee_angle_deg": {"label": "右膝关节角度", "order": 20, "decimals": 1},
    "knee_rom_deg": {"label": "膝关节运动范围", "order": 30, "decimals": 1},
    "ankle_vertical_range_px": {"label": "踝部垂直波动范围", "order": 40, "decimals": 1},
    "kick_periodicity": {"label": "打腿周期性", "order": 50, "decimals": None},
    "left_right_kick_timing": {"label": "左右打腿时序", "order": 60, "decimals": None},
    # head_trunk
    "head_vertical_range_px": {"label": "头部垂直波动范围", "order": 10, "decimals": 1},
    "head_shoulder_relative_offset": {"label": "头肩相对偏移", "order": 20, "decimals": 1},
    "head_body_synchrony": {"label": "头体同步性", "order": 30, "decimals": 3},
    "head_motion_spike_frames": {"label": "头部剧烈运动帧", "order": 40, "decimals": None},
    "trunk_vertical_stability": {"label": "躯干垂直稳定性", "order": 50, "decimals": 3},
}

# ── Per-page metric keys ──

PAGE_METRIC_KEYS: dict[str, list[str]] = {
    "body_posture_control": [
        "torso_axis_angle_deg", "body_axis_angle_deg", "hip_vertical_range_px",
        "shoulder_vertical_range_px", "body_angle_std_deg", "posture_stability_cv",
        "head_vertical_range_px", "head_shoulder_relative_offset",
        "head_body_synchrony", "head_motion_spike_frames", "trunk_vertical_stability",
    ],
    "upper_limb_kinematics": [
        "left_elbow_angle_deg", "right_elbow_angle_deg", "elbow_rom_deg",
        "normalized_wrist_trajectory", "arm_extension_ratio", "wrist_velocity_px_per_frame",
    ],
    "lower_limb_kinematics": [
        "left_knee_angle_deg", "right_knee_angle_deg", "knee_rom_deg",
        "ankle_vertical_range_px", "kick_periodicity", "left_right_kick_timing",
    ],
}


def _format_numeric(value: float, decimals: int | None) -> str | None:
    if decimals is None:
        return None
    return f"{value:.{decimals}f}"


def _format_complex_value(value, metric_key: str, config: dict) -> str | None:
    """Format dict-valued metrics into display strings."""
    if not isinstance(value, dict):
        return None
    if metric_key == "elbow_rom_deg":
        left = value.get("left")
        right = value.get("right")
        parts = []
        if left is not None:
            parts.append(f"左 {left:.1f}°")
        if right is not None:
            parts.append(f"右 {right:.1f}°")
        return " | ".join(parts) if parts else None
    if metric_key == "knee_rom_deg":
        left = value.get("left")
        right = value.get("right")
        parts = []
        if left is not None:
            parts.append(f"左 {left:.1f}°")
        if right is not None:
            parts.append(f"右 {right:.1f}°")
        return " | ".join(parts) if parts else None
    if metric_key == "ankle_vertical_range_px":
        left = value.get("left")
        right = value.get("right")
        parts = []
        if left is not None:
            parts.append(f"左 {left:.1f} px")
        if right is not None:
            parts.append(f"右 {right:.1f} px")
        return " | ".join(parts) if parts else None
    if metric_key in ("kick_periodicity", "left_right_kick_timing"):
        return str(value)
    return None


def _get(envelope, key: str, default=None):
    """Get a value from either a MetricEnvelope object or a plain dict."""
    if isinstance(envelope, dict):
        return envelope.get(key, default)
    return getattr(envelope, key, default)


def _project_envelope_to_metric(
    key: str, envelope, config: dict | None
) -> ReportMetric:
    """Convert one MetricEnvelope (object or dict) into a ReportMetric."""
    cfg = config or {}
    label = cfg.get("label", key)
    decimals = cfg.get("decimals")
    value = _get(envelope, "value")
    category = _get(envelope, "category", "body_posture")

    if isinstance(value, (float, int)):
        display_value = _format_numeric(value, decimals)
    elif isinstance(value, dict):
        display_value = _format_complex_value(value, key, cfg)
    elif isinstance(value, list):
        display_value = str(len(value)) + " 项"
    else:
        display_value = str(value) if value is not None else None

    reference_basis = _get(envelope, "reference_basis", "screen_horizontal")
    reference_basis_label = REFERENCE_BASIS_LABELS.get(reference_basis, reference_basis)

    provenance_raw = _get(envelope, "provenance", {})
    if hasattr(provenance_raw, "model_dump"):
        provenance_raw = provenance_raw.model_dump(mode="json")
    elif not isinstance(provenance_raw, dict):
        provenance_raw = {}

    return ReportMetric(
        key=key,
        label=label,
        category=category,  # type: ignore[arg-type]
        value=value,
        display_value=display_value,
        unit=_get(envelope, "unit"),
        availability=_get(envelope, "availability", "unavailable"),  # type: ignore[arg-type]
        confidence=_get(envelope, "confidence", 0.0),
        sample_count=_get(envelope, "sample_count", 0),
        reference_basis=reference_basis,  # type: ignore[arg-type]
        reference_basis_label=reference_basis_label,
        provenance=provenance_raw,
        details=_get(envelope, "details", {}),
    )


def build_report_metric_index(
    summary: dict[str, object],
) -> dict[str, ReportMetric]:
    """Build the immutable all_report_metrics index from the summary dict.

    Handles both MetricEnvelope objects and serialized dicts (from JSONB).
    """
    index: dict[str, ReportMetric] = {}
    for key, envelope in summary.items():
        if envelope is None:
            continue
        config = KINEMATICS_REPORT_METRICS.get(key)
        index[key] = _project_envelope_to_metric(key, envelope, config)
    return index


def select_report_metrics(
    index: dict[str, ReportMetric],
    keys: list[str],
) -> list[ReportMetric]:
    """Select and order ReportMetrics from the index for a page."""
    result = []
    for key in keys:
        if key in index:
            result.append(index[key])
    return result
