from app.services.annotation_quality.issue_codes import (
    EVENT_CATCH_START_MISSING,
    EVENT_HAND_ENTRY_MISSING,
    EVENT_KEYPOINT_WINDOW_EMPTY,
    EVENT_PULL_END_MISSING,
    LANDMARK_COVERAGE_LOW,
    COMPLETE_CYCLE_INSUFFICIENT,
    WATERLINE_MISSING,
    SWIM_DIRECTION_UNSET,
    SCALE_MISSING,
)
from app.services.annotation_quality.models import QualityIssue

CORE_KEYPOINTS: set[str] = {
    "shoulder", "elbow", "wrist", "hip", "knee", "ankle",
}


def compute_landmark_coverage(
    keypoint_frames: list[dict],
) -> dict[str, float]:
    total = len(keypoint_frames)
    counts: dict[str, int] = {}
    for kf in keypoint_frames:
        points = kf.get("points", {}) if isinstance(kf, dict) else {}
        for name in points:
            counts[name] = counts.get(name, 0) + 1
    coverage: dict[str, float] = {}
    for name in CORE_KEYPOINTS:
        coverage[name] = round(counts.get(name, 0) / max(total, 1), 4)
    left_right = {"left_" + n: counts.get("left_" + n, 0) / max(total, 1) for n in CORE_KEYPOINTS}
    right_variants = {"right_" + n: counts.get("right_" + n, 0) / max(total, 1) for n in CORE_KEYPOINTS}
    coverage.update(left_right)
    coverage.update(right_variants)
    return coverage


def check_landmark_coverage(
    keypoint_frames: list[dict],
    required_landmarks: list[str],
    min_coverage: float = 0.80,
) -> list[QualityIssue]:
    if not keypoint_frames:
        return []
    coverage = compute_landmark_coverage(keypoint_frames)
    issues: list[QualityIssue] = []
    for lm in required_landmarks:
        cov = coverage.get(lm, 0)
        if cov < min_coverage:
            issues.append(
                QualityIssue(
                    code=LANDMARK_COVERAGE_LOW,
                    category="coverage",
                    severity="warning",
                    blocking=False,
                    path=f"keypoint_frames.points.{lm}",
                    message=f"关键点 {lm} 覆盖率 {cov:.0%} 低于 {min_coverage:.0%}",
                    user_message=f"{lm} 的标注覆盖率仅 {cov:.0%}，相关分析结果的可靠性可能降低。",
                )
            )
    return issues


def check_required_events(
    events: list[dict],
    required_events: list[str],
) -> list[QualityIssue]:
    event_names = {e.get("name") for e in events if isinstance(e, dict)}
    issues: list[QualityIssue] = []
    for req in required_events:
        if req not in event_names:
            code = _event_missing_code(req)
            issues.append(
                QualityIssue(
                    code=code,
                    category="coverage",
                    severity="warning",
                    blocking=False,
                    path=f"events.{req}",
                    message=f"缺少必需事件 {req}",
                    user_message=_event_user_message(req),
                )
            )
    return issues


def _event_missing_code(event_name: str) -> str:
    mapping = {
        "hand_entry": EVENT_HAND_ENTRY_MISSING,
        "catch_start": EVENT_CATCH_START_MISSING,
        "pull_end": EVENT_PULL_END_MISSING,
    }
    return mapping.get(event_name, "REQUIRED_EVENT_MISSING")


def _event_user_message(event_name: str) -> str:
    messages = {
        "hand_entry": "缺少入水事件标记。请在 Kinovea 中补充入水标记。",
        "catch_start": "缺少抱水开始事件，抱水推进模块将无法准确计算阶段时长。",
        "pull_end": "缺少推水结束事件，划水阶段分析可能不完整。",
    }
    return messages.get(event_name, f"缺少 {event_name} 事件。")


def check_reference_elements(
    reference_lines: dict | None,
    swim_direction: str | None,
    scale: dict | None,
) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    if not reference_lines or not reference_lines.get("waterline"):
        issues.append(
            QualityIssue(
                code=WATERLINE_MISSING,
                category="coverage",
                severity="warning",
                blocking=False,
                path="reference_lines.waterline",
                message="未提供水面线，hip_depth_cm 未计算",
                user_message="缺少水面线，身体深度相关指标不可用。",
            )
        )
    if not swim_direction:
        issues.append(
            QualityIssue(
                code=SWIM_DIRECTION_UNSET,
                category="coverage",
                severity="info",
                blocking=False,
                path="swim_direction",
                message="未设置游泳方向，前伸距离以绝对值计算",
                user_message="未设置游泳方向，前伸距离将以绝对值计算。",
            )
        )
    if not scale or not scale.get("pixels_per_meter"):
        issues.append(
            QualityIssue(
                code=SCALE_MISSING,
                category="coverage",
                severity="warning",
                blocking=False,
                module="efficiency",
                path="scale.pixels_per_meter",
                message="缺少标尺换算系数",
                user_message="缺少标尺，速度与划幅相关指标不可用。",
            )
        )
    return issues


def check_cycle_completeness(
    events: list[dict],
    min_cycles: int = 2,
) -> list[QualityIssue]:
    hand_entries = [e for e in events if isinstance(e, dict) and e.get("name") == "hand_entry"]
    cycle_count = len(hand_entries)
    if cycle_count < min_cycles:
        return [
            QualityIssue(
                code=COMPLETE_CYCLE_INSUFFICIENT,
                category="coverage",
                severity="warning",
                blocking=False,
                path="events.hand_entry",
                message=f"完整划水周期数量 {cycle_count} 不足 {min_cycles}",
                user_message=f"仅 {cycle_count} 个入水事件，至少需要 {min_cycles} 个完整周期。",
            )
        ]
    return []
