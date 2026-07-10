"""side-view metrics 质量校验（MetricQualityReport 输出）。

与 annotation quality validator（标注输入质量）解耦：本模块校验
**指标计算前置条件**，并产出 MetricQualityReport，供 AnalysisQualityAggregator 消费。
"""

from typing import Any

from app.services.annotation_quality.evaluator import MetricQualityEvaluator
from app.services.annotation_quality.models import MetricQualityReport
from app.services.metrics.geometry import CORE_KEYPOINTS

CORE_METRIC_KEYS: list[str] = [
    "body_angle_deg_avg", "hip_depth_cm_avg", "streamline_index",
    "entry_angle_deg_avg", "front_reach_distance_cm_avg", "elbow_angle_deg_avg",
    "forearm_drop_angle_deg_avg", "knee_angle_deg_avg", "hip_angle_deg_avg",
    "ankle_extension_angle_deg_avg", "kick_frequency_hz",
    "stroke_rate_spm_avg", "stroke_length_m_avg", "average_speed_mps", "swolf",
]


def validate_metrics_inputs(
    annotation: dict,
    view_type: str,
    computed_keys: list[str],
    skipped_keys: list[str],
) -> dict:
    """聚合指标计算的质量检查结果（保持向后兼容的 dict 接口）。

    内部委托 MetricQualityEvaluator 输出 MetricQualityReport，
    同时兼容旧调用方期望的 dict 格式。
    """
    evaluator = MetricQualityEvaluator()
    report = evaluator.evaluate(
        metrics=annotation,
        computed_keys=computed_keys,
        skipped_keys=skipped_keys,
        annotation=annotation,
    )

    # 兼容旧 dict 输出（供 engine.py 直接消费）
    warnings: list[dict[str, str]] = []
    fps = annotation.get("fps")
    scale = annotation.get("scale") or {}
    ppm = scale.get("pixels_per_meter") if isinstance(scale, dict) else None
    events = annotation.get("events") or []
    keypoint_frames = annotation.get("keypoint_frames") or []
    reference_lines = annotation.get("reference_lines")
    distance_markers = annotation.get("distance_markers")
    swim_direction = annotation.get("swim_direction")

    event_names = {e.get("name") for e in events if isinstance(e, dict)}

    all_point_names: set[str] = set()
    for kf in keypoint_frames:
        pts = kf.get("points", {}) if isinstance(kf, dict) else {}
        all_point_names.update(pts.keys())
    core_present = any(
        set(required).issubset(all_point_names)
        for required in (
            set(CORE_KEYPOINTS),
            {f"left_{n}" for n in CORE_KEYPOINTS},
            {f"right_{n}" for n in CORE_KEYPOINTS},
        )
    )

    if not fps or fps <= 0:
        warnings.append({"code": "missing_fps", "message": "缺少有效 fps，无法计算时间与空间指标"})
    if len(keypoint_frames) < 3:
        warnings.append({"code": "insufficient_keypoint_frames", "message": f"关键点帧数 {len(keypoint_frames)} < 3，无法稳定计算角度"})
    if not core_present:
        warnings.append({"code": "missing_core_keypoints", "message": "缺少核心关键点（肩/肘/腕/髋/膝/踝）"})
    if view_type != "side":
        warnings.append({"code": "unsupported_camera_view", "message": f"camera_view={view_type} 不是 side，本引擎仅支持侧面视角"})
    if not ppm:
        warnings.append({"code": "missing_scale", "message": "缺少 scale.pixels_per_meter，距离/速度/划幅类指标降级为 null"})
    if "hand_entry" not in event_names:
        warnings.append({"code": "missing_hand_entry", "message": "缺少 hand_entry 事件，划频/划幅/周期类指标降级为 null"})
    if not reference_lines or not reference_lines.get("waterline"):
        warnings.append({"code": "missing_waterline", "message": "未提供水面线，hip_depth_cm 未计算"})
    if not distance_markers:
        warnings.append({"code": "no_phase_context", "message": "缺少 distance_markers，phase_metrics 为空，速度/划幅（距离版）降级"})
    if not swim_direction:
        warnings.append({"code": "swim_direction_unset", "message": "未设置 swim_direction，front_reach_distance_cm 以绝对值计算，方向未消歧"})

    return {
        "level": report.status if report.status in ("good", "warning", "error") else {"valid": "good", "warning": "warning", "invalid": "error"}.get(report.status, "warning"),
        "fps_present": bool(fps and fps > 0),
        "scale_present": bool(ppm),
        "camera_view": view_type,
        "waterline_present": bool(reference_lines and reference_lines.get("waterline")),
        "distance_markers_present": bool(distance_markers),
        "required_points_present": core_present,
        "required_events_present": "hand_entry" in event_names,
        "computed_metric_count": report.computed_metric_count,
        "skipped_metric_count": report.skipped_metric_count,
        "computed_metrics": computed_keys,
        "skipped_metrics": skipped_keys,
        "warnings": warnings,
        "metric_quality_report": report.model_dump(mode="json"),
    }
