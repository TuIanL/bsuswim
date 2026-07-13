SEVERITY_RANK = {
    "high": 3,
    "medium": 2,
    "low": 1,
}

SECTION_CONFIG = {
    "body_position": {
        "title": "身体位置与流线型效率分析",
        "metric_keys": [
            "body_angle_deg", "hip_depth_cm",
            "body_angle_deg_low_speed", "body_angle_deg_middle_speed", "body_angle_deg_high_speed",
        ],
    },
    "arm_entry": {
        "title": "上肢入水与前端支撑分析",
        "metric_keys": ["entry_angle_deg", "front_reach_distance_cm", "forearm_drop_angle_deg"],
    },
    "catch_pull": {
        "title": "上肢抱水与推进动作分析",
        "metric_keys": ["elbow_angle_deg", "catch_duration_sec", "pull_duration_sec"],
    },
    "leg_kick": {
        "title": "腿部技术角度分析",
        "metric_keys": ["knee_angle_deg", "hip_angle_deg", "ankle_extension_angle_deg", "kick_frequency_hz"],
    },
    "efficiency": {
        "title": "专项技术效率分析",
        "metric_keys": ["speed_mps", "stroke_rate_spm", "stroke_length_m", "swolf_value"],
    },
}


def group_diagnostics_by_section(diagnostics: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for d in diagnostics:
        key = d.get("section_key")
        if key:
            groups.setdefault(key, []).append(d)
    return groups


def derive_section_status(diagnostics: list[dict]) -> str:
    if not diagnostics:
        return "ok"
    severities = [d.get("severity", "low") for d in diagnostics]
    if "high" in severities:
        return "has_issues"
    if len(diagnostics) >= 3:
        return "has_issues"
    if "medium" in severities:
        return "needs_attention"
    return "minor_issues"


def build_section(key: str, config: dict, diags: list[dict], metrics: dict) -> dict:
    section_metrics = [m for m in config["metric_keys"] if m in metrics]

    return {
        "key": key,
        "title": config["title"],
        "status": derive_section_status(diags),
        "metrics": [{"key": k, "value": metrics[k], "evaluation": None} for k in section_metrics],
        "findings": [
            {
                "title": d["title"],
                "severity": d["severity"],
                "description": d.get("evidence") or d.get("reason", ""),
            }
            for d in diags
        ],
        "recommendations": [
            {"title": d["title"], "description": d.get("suggestion", "")}
            for d in diags
            if d.get("suggestion")
        ],
        "diagnostic_codes": [d.get("code") for d in diags if d.get("code")],
        "assets": [],
    }


def build_sections(metrics: dict, diagnostics: list[dict]) -> list[dict]:
    diag_by_section = group_diagnostics_by_section(diagnostics)
    sections = []
    for key, config in SECTION_CONFIG.items():
        diags = diag_by_section.get(key, [])
        sections.append(build_section(key, config, diags, metrics))
    return sections
