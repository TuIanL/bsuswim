"""AnnotationQualityValidator — 标注输入质量验证。"""

from datetime import datetime, timezone

from app.services.annotation_quality.checks.context_checks import (
    check_camera_view,
    check_video_context_exists,
    check_video_metadata,
)
from app.services.annotation_quality.checks.coverage_checks import (
    check_cycle_completeness,
    check_landmark_coverage,
    check_reference_elements,
    check_required_events,
)
from app.services.annotation_quality.checks.geometry_checks import (
    check_coordinate_validity,
    check_scale_validity,
)
from app.services.annotation_quality.checks.temporal_checks import (
    check_event_duplicates,
    check_event_order,
    check_fps_consistency,
    check_frame_bounds,
)
from app.services.annotation_quality.models import (
    AnnotationQualityReport,
    ModuleReadiness,
    QualityIssue,
    QualityProfileRef,
    QualityStatus,
    QualitySummary,
)
from app.services.annotation_quality.provider import QualityProfile, QualityProfileProvider


def derive_global_status(
    issues: list[QualityIssue],
    module_readiness: dict[str, ModuleReadiness],
    profile: QualityProfile,
) -> QualityStatus:
    global_blocking_issues = [i for i in issues if i.blocking and i.module is None]
    if global_blocking_issues:
        return "invalid"

    core_modules = {k for k, v in profile.modules.items() if v.core}
    blocked_core = {k for k in core_modules if module_readiness.get(k, ModuleReadiness()).status == "blocked"}
    if blocked_core and len(blocked_core) >= len(core_modules):
        return "invalid"

    available_core = {
        k for k in core_modules
        if module_readiness.get(k, ModuleReadiness()).status in ("ready", "degraded")
    }
    if len(available_core) < profile.global_gate.minimum_ready_core_modules:
        return "invalid"

    all_ready = all(m.status == "ready" for m in module_readiness.values())
    has_warnings = any(i.severity in ("warning", "error") for i in issues)

    if all_ready and not has_warnings:
        return "valid"

    return "warning"


def compute_module_readiness(
    issues: list[QualityIssue],
    profile: QualityProfile,
) -> dict[str, ModuleReadiness]:
    readiness: dict[str, ModuleReadiness] = {}
    for module_key, module_cfg in profile.modules.items():
        module_issues = [i for i in issues if i.module == module_key]
        blocking_for_module = [i.code for i in module_issues if i.blocking]
        warnings_for_module = [i.code for i in module_issues if not i.blocking and i.severity != "info"]

        if blocking_for_module:
            status = "blocked"
        elif warnings_for_module:
            status = "degraded"
        else:
            status = "ready"

        readiness[module_key] = ModuleReadiness(
            status=status,
            blocking_issues=blocking_for_module,
            warnings=warnings_for_module,
        )
    return readiness


class AnnotationQualityValidator:
    def __init__(self, profile_provider: QualityProfileProvider):
        self.profile_provider = profile_provider

    def validate(
        self,
        events: list[dict],
        keypoint_frames: list[dict],
        scale: dict | None,
        fps: float | None,
        frame_count: int | None,
        reference_lines: dict | None,
        swim_direction: str | None,
        video_fps: float | None = None,
        video_width: int | None = None,
        video_height: int | None = None,
        session_video: dict | None = None,
        view_type: str | None = None,
        profile_id: str = "side_technical_v1",
        source_revision: int = 0,
        validator_version: str = "1.0.0",
    ) -> AnnotationQualityReport:
        profile = self.profile_provider.get(profile_id)
        issues: list[QualityIssue] = []
        issues.extend(check_video_context_exists(session_video))
        if not keypoint_frames:
            issues.append(QualityIssue(
                code="REQUIRED_LANDMARK_MISSING",
                category="coverage",
                severity="error",
                blocking=True,
                message="不存在任何关键帧数据",
                user_message="标注中缺少关键点数据，无法进行分析。",
            ))
        if session_video:
            issues.extend(check_video_metadata(session_video))
        issues.extend(check_camera_view(view_type))
        issues.extend(check_frame_bounds(events or [], keypoint_frames or [], frame_count))
        issues.extend(check_fps_consistency(fps, video_fps))
        issues.extend(check_event_order(events or []))
        issues.extend(check_event_duplicates(events or []))
        issues.extend(check_coordinate_validity(keypoint_frames or [], video_width, video_height))
        issues.extend(check_scale_validity(scale))

        for module_key, module_cfg in profile.modules.items():
            issues.extend(check_required_events(events or [], module_cfg.required_events))
            issues.extend(check_landmark_coverage(keypoint_frames or [], module_cfg.required_landmarks, module_cfg.minimum_landmark_coverage))

        issues.extend(check_reference_elements(reference_lines, swim_direction, scale))
        issues.extend(check_cycle_completeness(events or []))

        module_readiness = compute_module_readiness(issues, profile)
        status = derive_global_status(issues, module_readiness, profile)

        blocking_count = sum(1 for i in issues if i.blocking)
        error_count = sum(1 for i in issues if i.severity == "error")
        warning_count = sum(1 for i in issues if i.severity == "warning")
        info_count = sum(1 for i in issues if i.severity == "info")

        passed = len([i for i in issues if i.severity not in ("error", "warning")])
        total = len(issues) if issues else 1
        score = int(passed / total * 100) if total > 0 else 100

        return AnnotationQualityReport(
            schema_version="annotation-quality.v2",
            status=status,
            score=score,
            source_revision=source_revision,
            validator_version=validator_version,
            profile=QualityProfileRef(id=profile.id, version=profile.version),
            validated_at=datetime.now(timezone.utc).isoformat(),
            summary=QualitySummary(
                blocking_count=blocking_count,
                error_count=error_count,
                warning_count=warning_count,
                info_count=info_count,
            ),
            issues=issues,
            module_readiness=module_readiness,
        )
