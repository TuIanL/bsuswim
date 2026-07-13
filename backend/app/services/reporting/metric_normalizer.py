METRIC_RENAME = {
    "body_angle_deg_avg": "body_angle_deg",
    "hip_depth_cm_avg": "hip_depth_cm",
    "elbow_angle_deg_avg": "elbow_angle_deg",
    "forearm_drop_angle_deg_avg": "forearm_drop_angle_deg",
    "knee_angle_deg_avg": "knee_angle_deg",
    "hip_angle_deg_avg": "hip_angle_deg",
    "ankle_extension_angle_deg_avg": "ankle_extension_angle_deg",
    "entry_angle_deg_avg": "entry_angle_deg",
    "front_reach_distance_cm_avg": "front_reach_distance_cm",
    "stroke_rate_spm_avg": "stroke_rate_spm",
    "stroke_length_m_avg": "stroke_length_m",
    "average_speed_mps": "speed_mps",
}

PASS_THROUGH = [
    "streamline_index",
    "technical_stability_score",
    "stroke_count",
    "kick_frequency_hz",
    "swolf_value",
]


def normalize_report_metrics(raw: dict) -> dict:
    summary = raw.get("summary") or raw
    canonical = {}
    for src, dst in METRIC_RENAME.items():
        if src in summary and summary[src] is not None:
            canonical[dst] = summary[src]
    for key in PASS_THROUGH:
        if key in summary and summary[key] is not None:
            canonical[key] = summary[key]
    swolf = summary.get("swolf")
    if isinstance(swolf, dict) and "value" in swolf:
        canonical["swolf_value"] = swolf["value"]
    return canonical


def flatten_phase_metrics(raw: dict) -> dict:
    result = {}
    for phase in raw.get("phase_metrics") or []:
        key = phase.get("phase_key")
        if not key:
            continue
        for m_key, m_val in (phase.get("metrics") or {}).items():
            if m_val is not None:
                result[f"{m_key}_{key}"] = m_val
    return result


PHASE_ALIASES = {
    "body_angle_deg_low_speed": "body_angle_low_speed_deg",
    "body_angle_deg_middle_speed": "body_angle_middle_speed_deg",
    "body_angle_deg_high_speed": "body_angle_high_speed_deg",
}


def apply_phase_aliases(flattened: dict) -> dict:
    result = dict(flattened)
    for new_key, alias_key in PHASE_ALIASES.items():
        if new_key in flattened and alias_key not in result:
            result[alias_key] = flattened[new_key]
    return result
