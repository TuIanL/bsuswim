# side-2d-kinematics Specification

## Purpose
Define the capability to compute side-view 2D kinematics (body posture, upper-limb, lower-limb, and head/trunk angles) from COCO17 keypoint frames without requiring events, scale, waterline, or distance markers. This calculator (`side_2d_kinematics`, schema `swim-side-kinematics.v1`) coexists with the legacy `side_view_metrics` calculator and produces only factual measurements, not diagnostics.

## Requirements
### Requirement: Calculate four groups of side 2D kinematics

The system SHALL calculate body posture, upper-limb, lower-limb, and head/trunk kinematics from side-view COCO17 keypoint frames without requiring events, scale, waterline, or distance markers.

#### Scenario: CVAT skeleton without semantic events
- **WHEN** a side-view normalized annotation contains valid COCO17 keypoint frames
- **AND** events, scale, waterline, and distance markers are absent
- **THEN** the system SHALL calculate all metrics supported by the available keypoints
- **AND** it SHALL NOT emit missing-event, missing-scale, or missing-waterline issues for this calculator

### Requirement: Every metric has a traceable envelope

Each metric SHALL include value, unit, sample_count, availability, confidence, source_frames, and reference_basis.

#### Scenario: Knee angle is unavailable
- **WHEN** no frame contains a valid hip-knee-ankle triplet
- **THEN** knee angle value SHALL be null
- **AND** sample_count SHALL be 0
- **AND** availability SHALL be unavailable
- **AND** source_frames SHALL be empty

### Requirement: Screen horizontal is not water surface

The system SHALL distinguish screen-horizontal from water-surface angles. All body-axis angle metrics SHALL use screen_horizontal as their reference basis.

#### Scenario: Body axis angle is calculated without a waterline
- **WHEN** body_axis_angle_deg is calculated
- **THEN** reference_basis SHALL be screen_horizontal
- **AND** the system MUST NOT label the metric as a waterline angle

### Requirement: Joint angles use joint geometry reference

Joint angles SHALL use the three-point joint geometry convention. The reference basis SHALL be joint_geometry.

#### Scenario: Elbow angle is calculated
- **WHEN** shoulder, elbow, and wrist are available
- **THEN** reference_basis SHALL be joint_geometry
- **AND** the value SHALL be the included shoulder-elbow-wrist angle

### Requirement: Side-specific COCO17 points are authoritative

Left/right COCO17 keypoints SHALL be the primary input for bilateral midpoint calculation. Single-side fallback SHALL be explicitly tracked.

#### Scenario: Bilateral keypoints are present
- **WHEN** left_shoulder and right_shoulder are available
- **THEN** shoulder_mid SHALL be their midpoint

#### Scenario: One shoulder is missing
- **WHEN** only one shoulder point is usable
- **THEN** the available point MAY be used as a fallback
- **AND** affected metrics SHALL be low_confidence
- **AND** quality SHALL record SINGLE_SIDE_FALLBACK

### Requirement: Temporal metrics respect frame mapping

Time-derivative metrics SHALL degrade when source-video frame mapping is unverified.

#### Scenario: Source frame mapping is unverified
- **WHEN** wrist velocity is calculated using annotation frame indices
- **AND** source-video frame mapping is not verified
- **THEN** wrist_velocity_px_per_frame SHALL be low_confidence
- **AND** representative frame extractable SHALL be false

### Requirement: New calculator does not replace legacy

The new side_2d_kinematics calculator SHALL coexist with the existing side_view_metrics calculator.

#### Scenario: Existing side_view_metrics is requested
- **WHEN** calculator=side_view_metrics
- **THEN** the existing swim-side-metrics.v1 calculation SHALL remain available

#### Scenario: New kinematics calculator is requested
- **WHEN** calculator=side_2d_kinematics
- **THEN** the system SHALL return swim-side-kinematics.v1
