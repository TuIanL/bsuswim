"""Kinematic visual artifact schema version and shared constants.

These constants back the `swim-kinematic-artifacts.v1` manifest contract
described in the change `add-kinematics-visual-artifact-generation`.
"""

from enum import StrEnum

SCHEMA_VERSION = "swim-kinematic-artifacts.v1"

GENERATOR_NAME = "kinematics_visuals"
GENERATOR_VERSION = "1.0.0"
STYLE_PROFILE = "kinematics_report_light_v1"
ARTIFACT_PLAN_VERSION = "artifact-plan.v1"

# --- Artifact types ---------------------------------------------------------
class ArtifactType(StrEnum):
    ANNOTATED_KEYFRAME = "annotated_keyframe"
    TIME_SERIES_CHART = "time_series_chart"
    TRAJECTORY_CHART = "trajectory_chart"
    RANGE_CHART = "range_chart"
    RADAR_CHART = "radar_chart"


# --- Status ----------------------------------------------------------------
class ArtifactStatus(StrEnum):
    READY = "ready"
    SKIPPED = "skipped"
    FAILED = "failed"


class ArtifactSetStatus(StrEnum):
    GENERATING = "generating"
    READY = "ready"
    PARTIAL = "partial"
    FAILED = "failed"


# --- Structured skip / error reason codes ----------------------------------
class SkipReason(StrEnum):
    METRIC_UNAVAILABLE = "metric_unavailable"
    INSUFFICIENT_SERIES_POINTS = "insufficient_series_points"
    METRIC_REVISION_STALE = "metric_revision_stale"
    FRAME_MAPPING_UNVERIFIED = "frame_mapping_unverified"
    SOURCE_VIDEO_MISSING = "source_video_missing"
    SOURCE_FRAME_MISSING = "source_frame_missing"
    VIDEO_DECODE_FAILED = "video_decode_failed"
    COORDINATE_SPACE_MISMATCH = "coordinate_space_mismatch"
    REFERENCE_BODY_LENGTH_UNAVAILABLE = "reference_body_length_unavailable"
    RADAR_INPUTS_INSUFFICIENT = "radar_inputs_insufficient"
    RENDER_FAILED = "render_failed"


# --- Artifact keys (stable, central) ---------------------------------------
# module_key -> list of (artifact_key, artifact_type)
ARTIFACT_KEYS: dict[str, list[tuple[str, ArtifactType]]] = {
    "body_posture": [
        ("body_posture.keyframe.body_axis_min", ArtifactType.ANNOTATED_KEYFRAME),
        ("body_posture.keyframe.body_axis_max", ArtifactType.ANNOTATED_KEYFRAME),
        ("body_posture.chart.angle_timeseries", ArtifactType.TIME_SERIES_CHART),
        ("body_posture.chart.hip_trajectory", ArtifactType.TRAJECTORY_CHART),
    ],
    "upper_limb": [
        ("upper_limb.keyframe.left_elbow_min", ArtifactType.ANNOTATED_KEYFRAME),
        ("upper_limb.keyframe.left_elbow_max", ArtifactType.ANNOTATED_KEYFRAME),
        ("upper_limb.keyframe.right_elbow_min", ArtifactType.ANNOTATED_KEYFRAME),
        ("upper_limb.keyframe.right_elbow_max", ArtifactType.ANNOTATED_KEYFRAME),
        ("upper_limb.keyframe.arm_extension_max", ArtifactType.ANNOTATED_KEYFRAME),
        ("upper_limb.chart.elbow_angle_timeseries", ArtifactType.TIME_SERIES_CHART),
        ("upper_limb.chart.joint_trajectories", ArtifactType.TRAJECTORY_CHART),
    ],
    "lower_limb": [
        ("lower_limb.keyframe.left_knee_min", ArtifactType.ANNOTATED_KEYFRAME),
        ("lower_limb.keyframe.left_knee_max", ArtifactType.ANNOTATED_KEYFRAME),
        ("lower_limb.keyframe.right_knee_min", ArtifactType.ANNOTATED_KEYFRAME),
        ("lower_limb.keyframe.right_knee_max", ArtifactType.ANNOTATED_KEYFRAME),
        ("lower_limb.chart.knee_angle_timeseries", ArtifactType.TIME_SERIES_CHART),
        ("lower_limb.chart.joint_trajectories", ArtifactType.TRAJECTORY_CHART),
    ],
    "head_trunk": [
        ("head_trunk.keyframe.head_motion_spike", ArtifactType.ANNOTATED_KEYFRAME),
    ],
    "overview": [
        ("overview.chart.range_comparison", ArtifactType.RANGE_CHART),
        ("overview.chart.stability_radar", ArtifactType.RADAR_CHART),
    ],
}

# Metric keys associated with each artifact (for display/selection metadata).
ARTIFACT_METRIC_KEYS: dict[str, list[str]] = {
    "body_posture.keyframe.body_axis_min": ["body_axis_angle_deg"],
    "body_posture.keyframe.body_axis_max": ["body_axis_angle_deg"],
    "body_posture.chart.angle_timeseries": ["torso_axis_angle_deg", "body_axis_angle_deg"],
    "body_posture.chart.hip_trajectory": ["hip_vertical_range_px"],
    "upper_limb.keyframe.left_elbow_min": ["left_elbow_angle_deg"],
    "upper_limb.keyframe.left_elbow_max": ["left_elbow_angle_deg"],
    "upper_limb.keyframe.right_elbow_min": ["right_elbow_angle_deg"],
    "upper_limb.keyframe.right_elbow_max": ["right_elbow_angle_deg"],
    "upper_limb.keyframe.arm_extension_max": ["arm_extension_ratio", "normalized_wrist_trajectory"],
    "upper_limb.chart.elbow_angle_timeseries": ["left_elbow_angle_deg", "right_elbow_angle_deg"],
    "upper_limb.chart.joint_trajectories": ["normalized_wrist_trajectory"],
    "lower_limb.keyframe.left_knee_min": ["left_knee_angle_deg"],
    "lower_limb.keyframe.left_knee_max": ["left_knee_angle_deg"],
    "lower_limb.keyframe.right_knee_min": ["right_knee_angle_deg"],
    "lower_limb.keyframe.right_knee_max": ["right_knee_angle_deg"],
    "lower_limb.chart.knee_angle_timeseries": ["left_knee_angle_deg", "right_knee_angle_deg"],
    "lower_limb.chart.joint_trajectories": [
        "left_knee_angle_deg",
        "right_knee_angle_deg",
        "knee_rom_deg",
    ],
    "head_trunk.keyframe.head_motion_spike": ["head_motion_spike_frames"],
    "overview.chart.range_comparison": [
        "elbow_rom_deg",
        "knee_rom_deg",
        "head_vertical_range_px",
        "hip_vertical_range_px",
        "body_angle_std_deg",
    ],
    "overview.chart.stability_radar": [
        "posture_stability_cv",
        "body_angle_std_deg",
        "kick_periodicity",
        "trunk_vertical_stability",
    ],
}

# Output dimensions.
KEYFRAME_WIDTH = 1600
KEYFRAME_HEIGHT = 900
CHART_WIDTH = 1200
CHART_HEIGHT = 675
RADAR_SIZE = 900

# Performance boundaries.
MAX_KEYFRAMES = 12
MAX_TIME_SERIES_POINTS = 600
MAX_TRAJECTORY_POINTS = 800
