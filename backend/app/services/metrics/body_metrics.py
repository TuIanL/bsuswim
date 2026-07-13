"""身体位置与流线型指标（A 组）。

- body_angle_deg：shoulder→ankle 连线与水平夹角（取 abs）
- hip_depth_cm：髋位深度，需 reference_lines.waterline
- streamline_index：0–100 内部复合子分（MVP 简化规则）
- body_line_deviation_cm：延期到 v2（需拟合参考线），本模块不产出
"""

from statistics import mean

from app.services.metrics.geometry import angle_to_horizontal, clamp, waterline_y_at_x


def calculate_body_position_metrics(annotation: dict, ppm: float | None) -> tuple[dict, list[dict]]:
    """返回 (summary 增量, time_series.body_angle_deg)。"""
    keypoint_frames = annotation.get("keypoint_frames") or []
    reference_lines = annotation.get("reference_lines") or {}

    body_angles: list[float] = []
    ts: list[dict] = []
    hip_depths_cm: list[float] = []

    waterline = reference_lines.get("waterline") if reference_lines else None

    for kf in keypoint_frames:
        if not isinstance(kf, dict):
            continue
        pts = kf.get("points", {})
        shoulder = pts.get("shoulder")
        ankle = pts.get("ankle")
        hip = pts.get("hip")
        frame = kf.get("frame", 0)
        time_sec = kf.get("time_sec", 0.0)

        ang = angle_to_horizontal(shoulder, ankle)
        if ang is not None:
            body_angles.append(ang)
            ts.append({"frame": frame, "time_sec": time_sec, "value": round(ang, 2)})

        if waterline and hip is not None:
            hip_xy = None
            if isinstance(hip, dict):
                hip_xy = (hip.get("x"), hip.get("y"))
            elif hasattr(hip, "x"):
                hip_xy = (hip.x, hip.y)
            if hip_xy is not None:
                wy = waterline_y_at_x(waterline, hip_xy[0])
                if wy is not None and ppm:
                    depth_px = hip_xy[1] - wy
                    hip_depths_cm.append(depth_px / ppm * 100.0)

    summary: dict = {}
    if body_angles:
        summary["body_angle_deg_avg"] = round(mean(body_angles), 2)
        summary["body_angle_deg_min"] = round(min(body_angles), 2)
        summary["body_angle_deg_max"] = round(max(body_angles), 2)

    hip_depth_computed = False
    if hip_depths_cm:
        summary["hip_depth_cm_avg"] = round(mean(hip_depths_cm), 2)
        hip_depth_computed = True

    # streamline_index：body_angle 与 hip_depth 惩罚，line_deviation 暂为 0（v2）
    body_penalty = min(summary.get("body_angle_deg_avg", 0) * 2.5, 40)
    hip_penalty = min(max(summary.get("hip_depth_cm_avg", 0), 0) * 1.5, 30)
    line_dev_penalty = 0.0
    summary["streamline_index"] = round(clamp(100 - body_penalty - hip_penalty - line_dev_penalty, 0, 100), 1)

    return summary, ts, hip_depth_computed
