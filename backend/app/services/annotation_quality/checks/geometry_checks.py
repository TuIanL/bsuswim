import math

from app.services.annotation_quality.issue_codes import (
    KEYPOINT_COORDINATE_INVALID,
    KEYPOINT_OUT_OF_BOUNDS,
    SCALE_INVALID,
)
from app.services.annotation_quality.models import QualityIssue


def check_coordinate_validity(
    keypoint_frames: list[dict],
    video_width: int | None,
    video_height: int | None,
) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    for kf in keypoint_frames:
        frame = kf.get("frame", 0) if isinstance(kf, dict) else 0
        points = kf.get("points", {}) if isinstance(kf, dict) else {}
        for name, pt in points.items():
            if isinstance(pt, dict):
                x = pt.get("x")
                y = pt.get("y")
            else:
                continue
            if x is None or y is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))) or (isinstance(y, float) and (math.isnan(y) or math.isinf(y))):
                issues.append(
                    QualityIssue(
                        code=KEYPOINT_COORDINATE_INVALID,
                        category="geometry",
                        severity="error",
                        blocking=True,
                        path=f"keypoint_frames.{frame}.points.{name}",
                        frame=frame,
                        message=f"关键点 {name} 在帧 {frame} 的坐标为无效值",
                        user_message=f"帧 {frame} 的 {name} 坐标无效，请检查标注。",
                    )
                )
            if video_width is not None and video_height is not None:
                if (isinstance(x, (int, float)) and x is not None and (x < -video_width * 0.02 or x >= video_width * 1.02)) or \
                   (isinstance(y, (int, float)) and y is not None and (y < -video_height * 0.02 or y >= video_height * 1.02)):
                    issues.append(
                        QualityIssue(
                            code=KEYPOINT_OUT_OF_BOUNDS,
                            category="geometry",
                            severity="warning",
                            blocking=False,
                            path=f"keypoint_frames.{frame}.points.{name}",
                            frame=frame,
                            message=f"关键点 {name} 在帧 {frame} 的坐标 ({x}, {y}) 超出画面 ({video_width}x{video_height})",
                            user_message=f"帧 {frame} 的 {name} 位置超出画面边缘，请检查标注。",
                        )
                    )
    return issues


def check_scale_validity(scale: dict | None) -> list[QualityIssue]:
    if not scale:
        return [
            QualityIssue(
                code=SCALE_INVALID,
                category="geometry",
                severity="error",
                blocking=True,
                module="efficiency",
                path="scale",
                message="缺少有效的标尺信息",
                user_message="缺少标尺信息，速度和划幅模块不可用。请在 Kinovea 中添加标尺。",
            )
        ]
    ppm = scale.get("pixels_per_meter")
    if not ppm or ppm <= 0:
        return [
            QualityIssue(
                code=SCALE_INVALID,
                category="geometry",
                severity="error",
                blocking=True,
                module="efficiency",
                path="scale.pixels_per_meter",
                message="scale.pixels_per_meter 无效",
                user_message="标尺换算系数无效，请检查 Kinovea 标尺设置。",
            )
        ]
    return []
