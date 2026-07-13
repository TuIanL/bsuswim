from app.services.annotation_quality.issue_codes import (
    SEQUENCE_COVERAGE_LOW,
    TIME_MAPPING_UNVERIFIED,
)
from app.services.annotation_quality.models import QualityIssue


def check_frame_mapping(
    frame_mapping: dict | None,
) -> list[QualityIssue]:
    if not frame_mapping:
        return []
    mode = frame_mapping.get("mode")
    verified = frame_mapping.get("verified", False)
    if mode in ("explicit",) and verified:
        return []
    if mode in ("affine", "identity") and not verified:
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
    return []


def check_sequence_coverage(
    annotated_frame_count: int | None,
    sequence_frame_count: int | None,
    analysis_ranges: list | None = None,
) -> list[QualityIssue]:
    if not sequence_frame_count or not annotated_frame_count:
        return []

    if analysis_ranges:
        total_planned = 0
        for r in analysis_ranges:
            start = r.get("start_annotation_frame", 0)
            end = r.get("end_annotation_frame", 0)
            total_planned += max(0, end - start + 1)
        if total_planned > 0 and annotated_frame_count >= total_planned:
            return []

    total = sequence_frame_count
    annotated = annotated_frame_count
    coverage_ratio = annotated / total if total > 0 else 0

    if coverage_ratio < 1.0:
        return [
            QualityIssue(
                code=SEQUENCE_COVERAGE_LOW,
                category="coverage",
                severity="info",
                blocking=False,
                path="annotation_coverage.annotated_frame_count",
                message=f"标注帧覆盖率 {coverage_ratio:.1%}（{annotated}/{total}）",
                user_message=f"仅标注了 {annotated}/{total} 帧，其余帧无骨架数据。",
            )
        ]
    return []
