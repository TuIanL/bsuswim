"""上肢技术指标（B 组）。

- entry_angle_deg：hand_entry 帧 shoulder→wrist 与水平夹角
- front_reach_distance_cm：wrist 相对 shoulder 的前伸距离，swim_direction 消歧符号
- elbow_angle_deg：shoulder-elbow-wrist 三点夹角（关键）
- forearm_drop_angle_deg：elbow→wrist 与水平夹角（前臂下压）
- catch_duration_sec / pull_duration_sec：抱水/推水阶段时长（事件 time_sec 差值）
"""

from statistics import mean

from app.services.metrics.geometry import angle_between_points, angle_to_horizontal


def _frame_index(keypoint_frames: list[dict]) -> dict[int, dict]:
    return {kf.get("frame"): kf for kf in keypoint_frames if isinstance(kf, dict)}


def _event_by_name(events: list[dict], name: str) -> list[dict]:
    return [e for e in events if isinstance(e, dict) and e.get("name") == name]


def _x_of(point) -> float | None:
    if isinstance(point, dict):
        return point.get("x")
    return getattr(point, "x", None)


def calculate_upper_limb_metrics(annotation: dict, ppm: float | None) -> dict:
    keypoint_frames = annotation.get("keypoint_frames") or []
    events = annotation.get("events") or []
    swim_direction = annotation.get("swim_direction")
    idx = _frame_index(keypoint_frames)

    front_reach: list[float] = []
    elbow_angles: list[float] = []
    forearm_drops: list[float] = []

    for kf in keypoint_frames:
        pts = kf.get("points", {})
        shoulder = pts.get("shoulder")
        elbow = pts.get("elbow")
        wrist = pts.get("wrist")

        # 前伸距离（需 ppm）
        if shoulder is not None and wrist is not None and ppm:
            sx = _x_of(shoulder)
            wx = _x_of(wrist)
            if sx is not None and wx is not None:
                raw = wx - sx
                if swim_direction == "left_to_right":
                    signed = raw
                elif swim_direction == "right_to_left":
                    signed = -raw
                else:
                    signed = abs(raw)
                front_reach.append(signed / ppm * 100.0)

        # 肘角（肩-肘-腕）
        ek = angle_between_points(shoulder, elbow, wrist)
        if ek is not None:
            elbow_angles.append(ek)

        # 前臂下压角（肘-腕 与水平）
        fd = angle_to_horizontal(elbow, wrist)
        if fd is not None:
            forearm_drops.append(fd)

    # 入水角：优先 hand_entry 帧；无事件时回退全部帧（estimated）
    entry_angles: list[float] = []
    hand_entries = _event_by_name(events, "hand_entry")
    target_frames = [idx.get(ev.get("frame")) for ev in hand_entries] if hand_entries else keypoint_frames
    for kf in target_frames:
        if not isinstance(kf, dict):
            continue
        pts = kf.get("points", {})
        ea = angle_to_horizontal(pts.get("shoulder"), pts.get("wrist"))
        if ea is not None:
            entry_angles.append(ea)

    summary: dict = {}
    if entry_angles:
        summary["entry_angle_deg_avg"] = round(mean(entry_angles), 2)
        summary["entry_estimated"] = not bool(hand_entries)
    if front_reach:
        summary["front_reach_distance_cm_avg"] = round(mean(front_reach), 2)
    if elbow_angles:
        summary["elbow_angle_deg_avg"] = round(mean(elbow_angles), 2)
    if forearm_drops:
        summary["forearm_drop_angle_deg_avg"] = round(mean(forearm_drops), 2)

    # 抱水/推水阶段时长
    catch_start = _event_by_name(events, "catch_start")
    pull_end = _event_by_name(events, "pull_end")
    if catch_start and pull_end:
        dur = mean([pe.get("time_sec", 0) - ce.get("time_sec", 0) for ce in catch_start for pe in pull_end])
        summary["catch_duration_sec"] = round(dur, 3)
        summary["pull_duration_sec"] = round(dur, 3)

    return summary
