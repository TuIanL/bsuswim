import math

from app.services.annotation_quality.issue_codes import (
    EVENT_DUPLICATED,
    EVENT_ORDER_INVALID,
    FRAME_INDEX_INVALID,
    FRAME_OUT_OF_RANGE,
    VIDEO_FPS_MISMATCH,
)
from app.services.annotation_quality.models import QualityIssue


def check_frame_bounds(events: list[dict], keypoint_frames: list[dict], frame_count: int | None) -> list[QualityIssue]:
    if frame_count is None:
        return []
    issues: list[QualityIssue] = []
    for evt in events:
        f = evt.get("frame", 0) if isinstance(evt, dict) else getattr(evt, "frame", 0)
        if f < 0 or f >= frame_count:
            issues.append(
                QualityIssue(
                    code=FRAME_OUT_OF_RANGE,
                    category="temporal",
                    severity="error",
                    blocking=True,
                    path="events",
                    frame=f,
                    message=f"事件帧号 {f} 超出视频范围 [0, {frame_count})",
                    user_message=f"帧号 {f} 超出视频范围。请检查 Kinovea 时间轴。",
                )
            )
    for kf in keypoint_frames:
        f = kf.get("frame", 0) if isinstance(kf, dict) else getattr(kf, "frame", 0)
        if f < 0 or f >= frame_count:
            issues.append(
                QualityIssue(
                    code=FRAME_OUT_OF_RANGE,
                    category="temporal",
                    severity="error",
                    blocking=True,
                    path="keypoint_frames",
                    frame=f,
                    message=f"关键帧帧号 {f} 超出视频范围 [0, {frame_count})",
                    user_message=f"帧号 {f} 超出视频范围。请检查标注帧率与视频帧率是否一致。",
                )
            )
    return issues


def check_fps_consistency(annotation_fps: float | None, video_fps: float | None) -> list[QualityIssue]:
    if annotation_fps is None or video_fps is None:
        return []
    issues: list[QualityIssue] = []
    diff = abs(annotation_fps - video_fps)
    if diff > 2.0:
        issues.append(
            QualityIssue(
                code=VIDEO_FPS_MISMATCH,
                category="temporal",
                severity="error",
                blocking=True,
                message=f"标注 fps ({annotation_fps}) 与视频 fps ({video_fps}) 差值为 {diff:.1f}",
                user_message=f"标注帧率 ({annotation_fps}fps) 与视频帧率 ({video_fps}fps) 不一致，可能导致帧号偏移。",
            )
        )
    elif diff > 0.5:
        issues.append(
            QualityIssue(
                code=VIDEO_FPS_MISMATCH,
                category="temporal",
                severity="warning",
                blocking=False,
                message=f"标注 fps ({annotation_fps}) 与视频 fps ({video_fps}) 差值为 {diff:.1f}",
                user_message=f"标注帧率与视频帧率存在微小偏差 ({diff:.1f}fps)，部分时间基准仅供参考。",
            )
        )
    return issues


def check_event_order(events: list[dict]) -> list[QualityIssue]:
    if not events:
        return []
    issues: list[QualityIssue] = []

    sides: set[str] = set()
    for e in events:
        if isinstance(e, dict):
            s = e.get("side", "unknown")
            sides.add(s)

    event_order = ["hand_entry", "catch_start", "pull_end", "hand_exit", "recovery"]
    cycle_boundary = "hand_entry"

    for side in sides:
        side_events = [e for e in events if isinstance(e, dict) and e.get("side", "unknown") == side]
        side_events.sort(key=lambda e: e.get("frame", 0))

        cycles = []
        current_cycle: list[dict] = []
        for e in side_events:
            if e.get("name") == cycle_boundary and current_cycle:
                cycles.append(current_cycle)
                current_cycle = []
            current_cycle.append(e)
        if current_cycle:
            cycles.append(current_cycle)

        for ci, cycle in enumerate(cycles):
            ordered = [e for e in cycle if e.get("name") in event_order]
            for i in range(1, len(ordered)):
                prev_idx = event_order.index(ordered[i - 1]["name"]) if ordered[i - 1]["name"] in event_order else -1
                curr_idx = event_order.index(ordered[i]["name"]) if ordered[i]["name"] in event_order else -1
                if prev_idx >= 0 and curr_idx >= 0 and curr_idx < prev_idx:
                    issues.append(
                        QualityIssue(
                            code=EVENT_ORDER_INVALID,
                            category="temporal",
                            severity="warning",
                            blocking=False,
                            path=f"events.side={side}.cycle={ci}",
                            message=f"{side} 侧周期 {ci} 中 {ordered[i - 1]['name']} 出现在 {ordered[i]['name']} 之前",
                            user_message=f"第 {ci + 1} 个动作周期中事件顺序异常：{ordered[i - 1]['label']} 晚于 {ordered[i]['label']}。",
                        )
                    )

    return issues


def check_event_duplicates(events: list[dict]) -> list[QualityIssue]:
    if not events:
        return []
    issues: list[QualityIssue] = []
    seen: dict[tuple, list[dict]] = {}
    for e in events:
        if isinstance(e, dict):
            key = (e.get("name"), e.get("side", "unknown"), e.get("frame"))
        else:
            key = None
        if key:
            if key not in seen:
                seen[key] = []
            seen[key].append(e)
    for key, dupes in seen.items():
        if len(dupes) > 1:
            issues.append(
                QualityIssue(
                    code=EVENT_DUPLICATED,
                    category="temporal",
                    severity="warning",
                    blocking=False,
                    path=f"events.{key[0]}.frame={key[1]}",
                    frame=key[2],
                    message=f"事件 {key[0]}（{key[1]}）在帧 {key[2]} 重复 {len(dupes)} 次",
                    user_message=f"帧 {key[2]} 存在 {len(dupes)} 个重复的 {key[0]} 事件。",
                )
            )
    return issues
