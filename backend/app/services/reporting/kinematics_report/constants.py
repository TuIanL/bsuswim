"""Five-page kinematics report: page plan, readiness policy, retest core keys."""

from app.schemas.kinematics_report import PageType

# ── Page Plan: maps page number to aggregation module and source modules ──

PAGE_PLAN = {
    1: {
        "page_type": "analysis_overview",
        "module_key": "overview",
        "source_module_keys": [],
    },
    2: {
        "page_type": "body_posture_control",
        "module_key": "body_posture_head_trunk",
        "source_module_keys": ["body_posture", "head_trunk"],
    },
    3: {
        "page_type": "upper_limb_kinematics",
        "module_key": "upper_limb",
        "source_module_keys": ["upper_limb"],
    },
    4: {
        "page_type": "lower_limb_kinematics",
        "module_key": "lower_limb",
        "source_module_keys": ["lower_limb"],
    },
    5: {
        "page_type": "review_and_retest",
        "module_key": "review_summary",
        "source_module_keys": ["body_posture", "head_trunk", "upper_limb", "lower_limb"],
    },
}

# ── Page Readiness Policy ──

PAGE_READINESS_POLICY = {
    "analysis_overview": {
        "required_metric_groups": [],
        "preferred_asset_groups": [],
    },
    "body_posture_control": {
        "required_metric_groups": [["body_axis_angle_deg", "torso_axis_angle_deg"]],
        "preferred_asset_groups": [["body_posture.chart.angle_timeseries"]],
    },
    "upper_limb_kinematics": {
        "required_metric_groups": [["left_elbow_angle_deg", "right_elbow_angle_deg"]],
        "preferred_asset_groups": [["upper_limb.chart.elbow_angle_timeseries"]],
    },
    "lower_limb_kinematics": {
        "required_metric_groups": [["left_knee_angle_deg", "right_knee_angle_deg"]],
        "preferred_asset_groups": [["lower_limb.chart.knee_angle_timeseries"]],
    },
}

# ── Attention rank (for sorting findings) ──

ATTENTION_RANK = {"high": 0, "medium": 1, "low": 2}

# ── Finding display limits ──

SUMMARY_TOP_FINDINGS_LIMIT = 3
PAGE_FINDINGS_LIMIT = 8

# ── Retest core keys (minimal stable set) ──

RETEST_CORE_KEYS = [
    "body_axis_angle_deg",
    "body_angle_std_deg",
    "hip_vertical_range_px",
    "elbow_rom_deg",
    "knee_rom_deg",
    "ankle_vertical_range_px",
    "head_vertical_range_px",
    "kick_periodicity",
]

# ── Asset order per page ──

PAGE_ASSET_ORDER: dict[str, list[str]] = {
    "body_posture_control": [
        "body_posture.keyframe.body_axis_min",
        "body_posture.keyframe.body_axis_max",
        "body_posture.chart.angle_timeseries",
        "body_posture.chart.hip_trajectory",
        "head_trunk.keyframe.head_motion_spike",
        "overview.chart.range_comparison",
    ],
    "upper_limb_kinematics": [
        "__selected__elbow_flexion",
        "__selected__elbow_extension",
        "upper_limb.chart.elbow_angle_timeseries",
        "upper_limb.chart.joint_trajectories",
        "upper_limb.keyframe.arm_extension_max",
    ],
    "lower_limb_kinematics": [
        "__selected__knee_flexion",
        "__selected__knee_extension",
        "lower_limb.chart.knee_angle_timeseries",
        "lower_limb.chart.joint_trajectories",
    ],
    "review_and_retest": [
        "overview.chart.range_comparison",
        "overview.chart.stability_radar",
    ],
}

# ── Reference basis display labels ──

REFERENCE_BASIS_LABELS: dict[str, str] = {
    "screen_horizontal": "画面水平线",
    "joint_geometry": "关节几何",
    "pixel": "像素",
    "normalized_body_length": "标准化体长",
    "frame_sequence": "帧序列",
}
