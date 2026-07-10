from app.services.annotation_quality.issue_codes import CAMERA_VIEW_UNSUPPORTED, VIDEO_CONTEXT_MISSING, VIDEO_METADATA_MISSING
from app.services.annotation_quality.models import QualityIssue


def check_video_context_exists(session_video: dict | None) -> list[QualityIssue]:
    if session_video is None:
        return []
    if not session_video.get("id"):
        return [
            QualityIssue(
                code=VIDEO_CONTEXT_MISSING,
                category="context",
                severity="error",
                blocking=True,
                message="无法获取关联视频信息",
                user_message="当前标注缺少关联视频，无法继续分析。",
            )
        ]
    return []


def check_video_metadata(session_video: dict) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    fps = session_video.get("fps")
    if not fps or fps <= 0:
        issues.append(
            QualityIssue(
                code=VIDEO_METADATA_MISSING,
                category="context",
                severity="error",
                blocking=True,
                message="无法获取关联视频的帧率",
                user_message="当前标注缺少视频帧率信息，无法检查帧号和时间。",
            )
        )
    return issues


def check_camera_view(view_type: str | None) -> list[QualityIssue]:
    if view_type and view_type != "side":
        return [
            QualityIssue(
                code=CAMERA_VIEW_UNSUPPORTED,
                category="context",
                severity="warning",
                blocking=False,
                message=f"camera_view={view_type} 不是 side",
                user_message=f"当前机位为 {view_type}，仅 side 视角支持完整分析。",
            )
        ]
    return []
