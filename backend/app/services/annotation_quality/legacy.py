"""Legacy quality v1 → v2 兼容适配器。"""

from app.services.annotation_quality.models import (
    AnnotationQualityReport,
    ModuleReadiness,
    QualityIssue,
    QualityProfileRef,
    QualityStatus,
    QualitySummary,
)


def normalize_quality_payload(raw: dict | None) -> AnnotationQualityReport:
    if raw and raw.get("schema_version") == "annotation-quality.v2":
        return AnnotationQualityReport.model_validate(raw)

    return migrate_legacy_quality_payload(raw or {})


def migrate_legacy_quality_payload(raw: dict) -> AnnotationQualityReport:
    level_map: dict[str, QualityStatus] = {
        "good": "valid",
        "warning": "warning",
        "error": "invalid",
    }
    old_level = raw.get("level", "error")
    status = level_map.get(old_level, "invalid")

    checks = raw.get("checks", [])
    issues: list[QualityIssue] = []
    warning_count = 0
    for c in checks:
        if isinstance(c, dict):
            code = f"LEGACY_{c.get('key', 'UNKNOWN')}"
            sev = "warning" if c.get("status") == "failed" else "info"
            if sev == "warning":
                warning_count += 1
            issues.append(QualityIssue(
                code=code,
                category="legacy",
                severity=sev,
                blocking=(c.get("status") == "failed" and c.get("key") in ("has_fps", "has_events", "has_keypoint_frames", "has_core_keypoints")),
                message=c.get("message", ""),
                user_message=c.get("message", ""),
            ))

    usable = raw.get("usable_modules", [])
    disabled = raw.get("disabled_modules", [])

    module_readiness_map: dict[str, str] = {
        "body_angle": "body_position",
        "elbow_angle": "catch_pull",
        "knee_angle": "leg_kick",
        "joint_positions": "body_position",
        "phase_duration": "catch_pull",
        "stroke_cycle": "efficiency",
        "event_timeline": "overview",
        "speed": "efficiency",
        "stroke_length": "efficiency",
        "hip_height_cm": "body_position",
        "distance_per_cycle": "efficiency",
    }

    module_readiness: dict[str, ModuleReadiness] = {}
    all_modules = ["overview", "body_position", "arm_entry", "catch_pull", "leg_kick", "efficiency"]
    for mod in all_modules:
        usables_for_mod = [k for k, v in module_readiness_map.items() if v == mod and k in usable]
        disabled_for_mod = [d.get("module") for d in disabled if isinstance(d, dict) and d.get("module") in module_readiness_map and module_readiness_map[d["module"]] == mod]

        if disabled_for_mod:
            module_readiness[mod] = ModuleReadiness(status="blocked", blocking_issues=disabled_for_mod)
        elif usables_for_mod:
            module_readiness[mod] = ModuleReadiness(status="ready")
        else:
            module_readiness[mod] = ModuleReadiness(status="degraded")

    score = raw.get("score")
    if score is None:
        passed = sum(1 for c in checks if isinstance(c, dict) and c.get("status") == "passed")
        total = len(checks) or 1
        score = int(passed / total * 100)

    return AnnotationQualityReport(
        schema_version="annotation-quality.v2",
        status=status,
        score=score,
        source_revision=raw.get("source_revision", 0),
        validator_version="legacy",
        profile=QualityProfileRef(id="unknown", version="0"),
        validated_at=raw.get("validated_at", ""),
        summary=QualitySummary(
            blocking_count=sum(1 for i in issues if i.blocking),
            error_count=sum(1 for i in issues if i.severity == "error"),
            warning_count=warning_count,
            info_count=sum(1 for i in issues if i.severity == "info"),
        ),
        issues=issues,
        module_readiness=module_readiness,
    )
