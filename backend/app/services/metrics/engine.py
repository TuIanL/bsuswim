"""side-view metrics 引擎主入口。

把 normalized annotation（dict）计算成固定 schema 的事实指标。本模块不含任何
诊断逻辑；诊断交给 Change #5，报告装配交给 Change #6。

入口：``calculate_side_view_metrics(annotation, view_type) -> dict(SideViewMetrics)``
"""

from statistics import mean

from app.services.metrics.body_metrics import calculate_body_position_metrics
from app.services.metrics.leg_metrics import calculate_leg_metrics
from app.services.metrics.quality import validate_metrics_inputs
from app.services.metrics.rhythm_metrics import calculate_rhythm_efficiency_metrics
from app.services.metrics.upper_limb_metrics import calculate_upper_limb_metrics


def _ppm(annotation: dict) -> float | None:
    scale = annotation.get("scale") or {}
    if isinstance(scale, dict):
        return scale.get("pixels_per_meter")
    return None


def _build_phase_metrics(annotation: dict, fps: float, body_ts: list[dict], cycles: list[dict]) -> list[dict]:
    """仅当 distance_markers 存在时，按瞬时速度分 low/middle/high 三阶段。"""
    distance_markers = annotation.get("distance_markers") or []
    if len(distance_markers) < 2 or not fps:
        return []

    dm = sorted(distance_markers, key=lambda m: m.get("frame", 0))
    seg_speeds: list[float] = []
    seg_times: list[float] = []
    for i in range(1, len(dm)):
        d0, d1 = dm[i - 1], dm[i]
        dt = (d1.get("frame", 0) - d0.get("frame", 0)) / fps
        dd = d1.get("distance_m", 0) - d0.get("distance_m", 0)
        if dt > 0:
            seg_speeds.append(dd / dt)
            seg_times.append(d1.get("time_sec", d1.get("frame", 0) / fps))

    if len(seg_speeds) < 2:
        return []

    lo = min(seg_speeds)
    hi = max(seg_speeds)
    if hi == lo:
        return []
    mid1 = lo + (hi - lo) / 3.0
    mid2 = lo + 2.0 * (hi - lo) / 3.0

    def band(sp: float) -> str:
        if sp < mid1:
            return "low_speed"
        if sp < mid2:
            return "middle_speed"
        return "high_speed"

    # 把每个关键点帧（带 body_angle）归入速度阶段
    bands: dict[str, list[dict]] = {"low_speed": [], "middle_speed": [], "high_speed": []}
    for pt in body_ts:
        # 用其 time_sec 找最近 seg 速度
        t = pt.get("time_sec", 0)
        nearest = min(range(len(seg_times)), key=lambda i: abs(seg_times[i] - t))
        bands[band(seg_speeds[nearest])].append(pt)

    label_map = {
        "low_speed": ("低速阶段", lo),
        "middle_speed": ("过渡阶段", (mid1 + mid2) / 2.0),
        "high_speed": ("高速阶段", hi),
    }
    phase_metrics: list[dict] = []
    for key, (label, speed) in label_map.items():
        pts = bands[key]
        if not pts:
            continue
        rep = min(pts, key=lambda p: abs(p.get("time_sec", 0) - mean([x.get("time_sec", 0) for x in pts])))
        body_vals = [p["value"] for p in pts if p.get("value") is not None]
        phase_metrics.append(
            {
                "phase_key": key,
                "label": label,
                "speed_mps": round(speed, 3),
                "representative_frame": rep.get("frame"),
                "metrics": {
                    "body_angle_deg": round(mean(body_vals), 2) if body_vals else None,
                },
            }
        )
    return phase_metrics


def calculate_side_view_metrics(annotation: dict, view_type: str) -> dict:
    """计算侧面视角技术指标，返回 SideViewMetrics 结构的 dict。

    :param annotation: normalized annotation dict（含 fps/scale/events/keypoint_frames/
                        reference_lines/distance_markers/swim_direction）
    :param view_type: 机位，来自 session_videos.view_type（"side" 等）
    """
    ppm = _ppm(annotation)
    fps = annotation.get("fps") or 0

    summary: dict = {}
    computed_keys: list[str] = []
    skipped_keys: list[str] = []

    # ── 四组指标 ──
    body_summary, body_ts, hip_depth_ok = calculate_body_position_metrics(annotation, ppm)
    summary.update(body_summary)

    upper = calculate_upper_limb_metrics(annotation, ppm)
    summary.update(upper)

    leg = calculate_leg_metrics(annotation)
    summary.update(leg)

    rhythm, cycles = calculate_rhythm_efficiency_metrics(annotation, ppm)
    summary.update(rhythm)

    # ── 计算/跳过追踪（用于 quality）──
    core_metric_keys = [
        "body_angle_deg_avg",
        "hip_depth_cm_avg",
        "streamline_index",
        "entry_angle_deg_avg",
        "front_reach_distance_cm_avg",
        "elbow_angle_deg_avg",
        "forearm_drop_angle_deg_avg",
        "knee_angle_deg_avg",
        "hip_angle_deg_avg",
        "ankle_extension_angle_deg_avg",
        "kick_frequency_hz",
        "stroke_rate_spm_avg",
        "stroke_length_m_avg",
        "average_speed_mps",
        "swolf",
    ]
    for k in core_metric_keys:
        if k in summary and summary[k] is not None:
            computed_keys.append(k)
        else:
            skipped_keys.append(k)

    # ── phase_metrics（仅当 distance_markers 存在）──
    phase_metrics = _build_phase_metrics(annotation, fps, body_ts, cycles)
    if not phase_metrics:
        skipped_keys.append("phase_metrics")

    # ── technical_stability_score：整体复合分（MVP 先等于 streamline_index）──
    if "streamline_index" in summary:
        summary["technical_stability_score"] = summary["streamline_index"]

    # ── 组装 ──
    time_series: dict = {}
    if body_ts:
        time_series["body_angle_deg"] = body_ts

    quality = validate_metrics_inputs(annotation, view_type, computed_keys, skipped_keys)

    return {
        "schema_version": "swim-side-metrics.v1",
        "camera_view": view_type or "side",
        "summary": summary,
        "time_series": time_series,
        "cycles": cycles,
        "phase_metrics": phase_metrics,
        "quality": quality,
    }
