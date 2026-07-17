from app.services.annotation_quality.issue_codes import (
    ANALYSIS_RANGE_NOT_COVERED,
    FPS_UNVERIFIED,
    SEQUENCE_COVERAGE_LOW,
    TIME_MAPPING_MISSING,
    TIME_MAPPING_UNVERIFIED,
)
from app.services.annotation_quality.models import QualityIssue


def check_frame_mapping(
    frame_mapping: dict | None,
    *,
    required: bool = False,
) -> list[QualityIssue]:
    if not frame_mapping:
        if required:
            return [
                QualityIssue(
                    code=TIME_MAPPING_MISSING,
                    category="coverage",
                    severity="error",
                    blocking=True,
                    path="frame_mapping",
                    message="帧映射缺失，时间相关指标不可用",
                    user_message="缺少帧映射信息，速度与频率类指标不可用。",
                )
            ]
        return []

    if frame_mapping.get("verified") is True:
        return []

    return [
        QualityIssue(
            code=TIME_MAPPING_UNVERIFIED,
            category="coverage",
            severity="warning",
            blocking=False,
            path="frame_mapping.verified",
            message="帧映射未经确认，时间相关指标不可用",
            user_message="标注帧与视频帧的对应关系未经确认，速度与划频指标不可用。请在解析时提供帧映射确认。",
        )
    ]


def check_fps_verified(
    video_metadata: dict | None,
) -> list[QualityIssue]:
    if not video_metadata:
        return []
    if video_metadata.get("fps_verified") is False:
        return [
            QualityIssue(
                code=FPS_UNVERIFIED,
                category="coverage",
                severity="warning",
                blocking=False,
                path="video.fps_verified",
                message="视频帧率未经确认，时间相关指标不可用",
                user_message="视频帧率未经确认，时间相关指标不可用。请确保视频帧率信息正确。",
            )
        ]
    return []


def contiguous_ranges_cover(
    annotated_ranges: list[dict],
    analysis_ranges: list[dict],
) -> bool:
    def _expand_ranges(ranges: list[dict]) -> set[int]:
        frames: set[int] = set()
        for r in ranges:
            start = r.get("start_annotation_frame", r.get("start_frame", 0))
            end = r.get("end_annotation_frame", r.get("end_frame", 0))
            frames.update(range(start, end + 1))
        return frames

    annotated_frames = _expand_ranges(annotated_ranges)
    for r in analysis_ranges:
        start = r.get("start_annotation_frame", r.get("start_frame", 0))
        end = r.get("end_annotation_frame", r.get("end_frame", 0))
        for f in range(start, end + 1):
            if f not in annotated_frames:
                return False
    return True


def check_sequence_coverage(
    annotated_frame_count: int | None,
    sequence_frame_count: int | None,
    *,
    annotated_ranges: list[dict] | None = None,
    analysis_ranges: list[dict] | None = None,
) -> list[QualityIssue]:
    issues: list[QualityIssue] = []

    if analysis_ranges and annotated_ranges:
        if contiguous_ranges_cover(annotated_ranges, analysis_ranges):
            return []
        issues.append(
            QualityIssue(
                code=ANALYSIS_RANGE_NOT_COVERED,
                category="coverage",
                severity="error",
                blocking=True,
                path="analysis_ranges",
                message="分析区间存在未被标注的帧",
                user_message="所选分析范围中存在未被标注的帧，请检查标注或调整分析范围。",
            )
        )
        return issues

    if sequence_frame_count and annotated_frame_count:
        if annotated_frame_count < sequence_frame_count:
            coverage_ratio = annotated_frame_count / sequence_frame_count
            issues.append(
                QualityIssue(
                    code=SEQUENCE_COVERAGE_LOW,
                    category="coverage",
                    severity="info",
                    blocking=False,
                    path="annotation_coverage.annotated_frame_count",
                    message=f"标注帧覆盖率 {coverage_ratio:.1%}（{annotated_frame_count}/{sequence_frame_count}）",
                    user_message=f"仅标注了 {annotated_frame_count}/{sequence_frame_count} 帧，其余帧无骨架数据。",
                )
            )

    return issues
