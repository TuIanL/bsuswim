"""Legacy compatibility wrapper - delegates to annotation_quality/ service.

Kept for backward compatibility. New code should use
AnnotationQualityValidator directly.
"""

from app.services.annotation_quality.checks.coverage_checks import compute_landmark_coverage
from app.services.annotation_quality.legacy import normalize_quality_payload, migrate_legacy_quality_payload
from app.services.annotation_quality.models import AnnotationQualityReport
from app.schemas.normalized_annotation import AnnotationQuality as AnnotationQualityV1, QualityCheck

CORE_KEYPOINTS: set[str] = {
    "shoulder", "elbow", "wrist", "hip", "knee", "ankle",
    "right_shoulder", "right_elbow", "right_wrist", "right_hip", "right_knee", "right_ankle",
    "left_shoulder", "left_elbow", "left_wrist", "left_hip", "left_knee", "left_ankle",
}

REQUIRED_KEYPOINTS_LEFT: set[str] = {"left_shoulder", "left_elbow", "left_wrist", "left_hip", "left_knee", "left_ankle"}
REQUIRED_KEYPOINTS_RIGHT: set[str] = {"right_shoulder", "right_elbow", "right_wrist", "right_hip", "right_knee", "right_ankle"}
REQUIRED_KEYPOINTS_PLAIN: set[str] = {"shoulder", "elbow", "wrist", "hip", "knee", "ankle"}


def check_has_fps(fps: float | None) -> QualityCheck:
    if fps and fps > 0:
        return QualityCheck(key="has_fps", status="passed", message=f"已提供 fps = {fps}")
    return QualityCheck(key="has_fps", status="failed", message="缺少有效的 fps，无法进行时间基准换算")


def check_has_events(events: list | None) -> QualityCheck:
    if events and len(events) > 0:
        return QualityCheck(key="has_events", status="passed", message=f"已提供 {len(events)} 个关键事件")
    return QualityCheck(key="has_events", status="failed", message="缺少关键事件，无法进行阶段分析")


def check_has_keypoint_frames(keypoint_frames: list | None) -> QualityCheck:
    if keypoint_frames and len(keypoint_frames) > 0:
        return QualityCheck(key="has_keypoint_frames", status="passed", message=f"已提供 {len(keypoint_frames)} 个关键帧")
    return QualityCheck(key="has_keypoint_frames", status="failed", message="缺少关键帧关键点数据")


def check_has_core_keypoints(keypoint_frames: list | None) -> QualityCheck:
    if not keypoint_frames:
        return QualityCheck(key="has_core_keypoints", status="failed", message="无关键帧数据，无法检查关键点覆盖")
    all_point_names: set[str] = set()
    for kf in keypoint_frames:
        points = kf.get("points", {}) if isinstance(kf, dict) else getattr(kf, "points", {})
        all_point_names.update(points.keys())
    has_plain = REQUIRED_KEYPOINTS_PLAIN.issubset(all_point_names)
    has_left = REQUIRED_KEYPOINTS_LEFT.issubset(all_point_names)
    has_right = REQUIRED_KEYPOINTS_RIGHT.issubset(all_point_names)
    if has_plain or has_left or has_right:
        side = "双侧" if (has_left and has_right) else ("左侧" if has_left else ("右侧" if has_right else "非侧标"))
        return QualityCheck(key="has_core_keypoints", status="passed", message=f"核心关键点完整（{side}）")
    missing = REQUIRED_KEYPOINTS_PLAIN - all_point_names
    return QualityCheck(
        key="has_core_keypoints",
        status="failed",
        message=f"缺少核心关键点: {', '.join(sorted(missing))}",
    )


def check_has_scale(scale: dict | None) -> QualityCheck:
    if scale and scale.get("pixels_per_meter"):
        return QualityCheck(
            key="has_scale",
            status="passed",
            message=f"已识别标尺信息，pixels_per_meter = {scale['pixels_per_meter']}",
        )
    return QualityCheck(key="has_scale", status="failed", message="缺少标尺信息，速度和划幅模块不可用")


def check_event_frame_range(events: list | None, frame_count: int | None) -> QualityCheck:
    if not events or frame_count is None:
        return QualityCheck(key="event_frame_range_valid", status="passed", message="跳过帧范围检查（无事件或无帧数）")
    for evt in events:
        f = evt.get("frame", 0) if isinstance(evt, dict) else getattr(evt, "frame", 0)
        if f > frame_count:
            return QualityCheck(
                key="event_frame_range_valid",
                status="failed",
                message=f"事件帧号 {f} 超出视频帧数 {frame_count}",
            )
    return QualityCheck(key="event_frame_range_valid", status="passed", message="事件帧号范围有效")


def check_keypoint_frame_range(keypoint_frames: list | None, frame_count: int | None) -> QualityCheck:
    if not keypoint_frames or frame_count is None:
        return QualityCheck(key="keypoint_frame_range_valid", status="passed", message="跳过帧范围检查（无关键帧或无帧数）")
    for kf in keypoint_frames:
        f = kf.get("frame", 0) if isinstance(kf, dict) else getattr(kf, "frame", 0)
        if f > frame_count:
            return QualityCheck(
                key="keypoint_frame_range_valid",
                status="failed",
                message=f"关键帧帧号 {f} 超出视频帧数 {frame_count}",
            )
    return QualityCheck(key="keypoint_frame_range_valid", status="passed", message="关键帧帧号范围有效")


def evaluate_quality(
    *,
    fps: float | None,
    events: list | None = None,
    keypoint_frames: list | None = None,
    scale: dict | None = None,
    frame_count: int | None = None,
) -> AnnotationQualityV1:
    events = events or []
    keypoint_frames = keypoint_frames or []

    checks: list[QualityCheck] = [
        check_has_fps(fps),
        check_has_events(events),
        check_has_keypoint_frames(keypoint_frames),
        check_has_core_keypoints(keypoint_frames),
        check_has_scale(scale),
    ]
    if frame_count is not None:
        checks.append(check_event_frame_range(events, frame_count))
        checks.append(check_keypoint_frame_range(keypoint_frames, frame_count))

    failed_keys = {c.key for c in checks if c.status == "failed"}
    critical_failures = {"has_fps", "has_events", "has_keypoint_frames", "has_core_keypoints"}
    if critical_failures & failed_keys:
        level: str = "error"
    elif "has_scale" in failed_keys:
        level = "warning"
    else:
        level = "good"

    passed = sum(1 for c in checks if c.status == "passed")
    total = len(checks)
    score = int(passed / total * 100) if total > 0 else 0

    usable_modules: list[str] = []
    disabled_modules: list[dict[str, str]] = []

    if "has_keypoint_frames" not in failed_keys and "has_core_keypoints" not in failed_keys:
        usable_modules.extend(["body_angle", "elbow_angle", "knee_angle", "joint_positions"])
    else:
        disabled_modules.append({"module": "joint_angles", "reason": "缺少核心关键点数据"})

    if "has_events" not in failed_keys:
        usable_modules.extend(["phase_duration", "stroke_cycle", "event_timeline"])
    else:
        disabled_modules.append({"module": "phase_analysis", "reason": "缺少关键事件数据"})

    if "has_scale" not in failed_keys:
        usable_modules.extend(["speed", "stroke_length", "hip_height_cm", "distance_per_cycle"])
    else:
        disabled_modules.append({"module": "speed_distance", "reason": "缺少标尺信息"})

    return AnnotationQualityV1(
        level=level,
        score=score,
        checks=checks,
        usable_modules=usable_modules,
        disabled_modules=disabled_modules,
    )
