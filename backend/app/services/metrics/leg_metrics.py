"""腿部技术指标（C 组）。

- knee_angle_deg：hip-knee-ankle 三点夹角（关键）
- hip_angle_deg：shoulder-hip-knee 夹角
- ankle_extension_angle_deg：小腿（knee→ankle）与竖直向下参考线的夹角（踝伸展近似，
  待 foot/toe 关键点补充后替换为膝-踝-趾）
- kick_frequency_hz：kick_downbeat 事件计数 / 时长；无事件则跳过（不阻塞）
"""

import math
from statistics import mean

from app.services.metrics.geometry import angle_between_points, angle_to_horizontal


def _vertical_down() -> tuple[float, float]:
    return (0.0, 1.0)


def calculate_leg_metrics(annotation: dict) -> dict:
    keypoint_frames = annotation.get("keypoint_frames") or []
    events = annotation.get("events") or []
    fps = annotation.get("fps") or 0

    knee_angles: list[float] = []
    hip_angles: list[float] = []
    ankle_ext: list[float] = []

    for kf in keypoint_frames:
        if not isinstance(kf, dict):
            continue
        pts = kf.get("points", {})
        shoulder = pts.get("shoulder")
        hip = pts.get("hip")
        knee = pts.get("knee")
        ankle = pts.get("ankle")

        ka = angle_between_points(hip, knee, ankle)
        if ka is not None:
            knee_angles.append(ka)

        ha = angle_between_points(shoulder, hip, knee)
        if ha is not None:
            hip_angles.append(ha)

        # 踝伸展近似：小腿向量 (knee→ankle) 与竖直向下参考线的夹角
        if knee is not None and ankle is not None:
            kx = knee.get("x") if isinstance(knee, dict) else getattr(knee, "x", None)
            ky = knee.get("y") if isinstance(knee, dict) else getattr(knee, "y", None)
            ax = ankle.get("x") if isinstance(ankle, dict) else getattr(ankle, "x", None)
            ay = ankle.get("y") if isinstance(ankle, dict) else getattr(ankle, "y", None)
            if None not in (kx, ky, ax, ay):
                shank = (ax - kx, ay - ky)
                vd = _vertical_down()

                m1 = math.hypot(*shank)
                m2 = math.hypot(*vd)
                if m1 and m2:
                    cos_t = (shank[0] * vd[0] + shank[1] * vd[1]) / (m1 * m2)
                    cos_t = max(-1.0, min(1.0, cos_t))
                    ankle_ext.append(math.degrees(math.acos(cos_t)))

    summary: dict = {}
    if knee_angles:
        summary["knee_angle_deg_avg"] = round(mean(knee_angles), 2)
        summary["knee_angle_deg_min"] = round(min(knee_angles), 2)
        summary["knee_angle_deg_max"] = round(max(knee_angles), 2)
    if hip_angles:
        summary["hip_angle_deg_avg"] = round(mean(hip_angles), 2)
    if ankle_ext:
        summary["ankle_extension_angle_deg_avg"] = round(mean(ankle_ext), 2)

    # 打腿频率
    kicks = [e for e in events if isinstance(e, dict) and e.get("name") == "kick_downbeat"]
    if len(kicks) >= 2 and fps:
        frames = sorted(e.get("frame", 0) for e in kicks)
        duration_sec = (frames[-1] - frames[0]) / fps
        if duration_sec > 0:
            summary["kick_frequency_hz"] = round(len(kicks) / duration_sec, 3)

    return summary
