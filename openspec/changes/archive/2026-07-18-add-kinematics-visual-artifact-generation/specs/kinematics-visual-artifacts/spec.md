# kinematics-visual-artifacts Specification

## Purpose

Define the capability to convert an exact `swim-side-kinematics.v1` AnnotationMetric and its corresponding side-view video and COCO17 annotation into persistent, traceable visual assets for later HTML, PDF and longitudinal-report reuse.

## ADDED Requirements

### Requirement: Generate artifacts from an exact metric record

The system SHALL generate visual artifacts from an explicitly selected AnnotationMetric record.

#### Scenario: A current side_2d_kinematics metric is requested

- **WHEN** a user requests artifact generation for an AnnotationMetric
- **AND** calculator is `side_2d_kinematics`
- **AND** schema_version is `swim-side-kinematics.v1`
- **AND** source_revision equals the current NormalizedAnnotation revision
- **THEN** the system SHALL create or return a matching artifact set

#### Scenario: Metric revision is stale

- **WHEN** source_revision differs from the current annotation revision
- **THEN** the system SHALL return 409 `metric_revision_stale`
- **AND** force mode SHALL NOT bypass the revision check

### Requirement: Reject null source revision

The system SHALL reject artifact generation when the source AnnotationMetric does not record a source_revision, because traceability requires a known annotation revision.

#### Scenario: AnnotationMetric has no source_revision

- **WHEN** an artifact generation is requested for an AnnotationMetric
- **AND** source_revision is null
- **THEN** the system SHALL return 422
- **AND** SHALL NOT proceed with generation

### Requirement: Persist a stable artifact manifest

Every artifact set SHALL record source metric identity, source annotation revision, generator version, style profile, generation signature, status, artifacts and warnings.

#### Scenario: An artifact set is persisted and read back

- **WHEN** a generation completes
- **THEN** every manifest artifact SHALL expose the fields listed below
- **AND** the manifest SHALL be returned by the read API

Every manifest artifact SHALL expose:

- artifact_key
- artifact_type
- module_key
- metric_keys
- annotation_frame and source_video_frame where applicable
- annotation/source frame range where applicable
- relative storage_path
- public URL
- mime_type
- width and height
- checksum_sha256
- source_annotation_revision
- generator_version
- status
- structured skip or failure reason

### Requirement: Generate five visual artifact families

The system SHALL support:

1. annotated keyframes;
2. joint-angle time-series charts;
3. joint-trajectory charts;
4. motion-range comparison charts;
5. clip-stability radar charts.

#### Scenario: Only chart data is available

- **WHEN** frame mapping is unverified
- **AND** metric time_series and ranges are available
- **THEN** annotated keyframes SHALL be skipped
- **AND** independent charts SHALL still be generated
- **AND** the artifact set status SHALL be partial

### Requirement: Annotated keyframes use verified video mapping

Annotated keyframes SHALL only be extracted from a source video when source-frame mapping is verified.

#### Scenario: Verified mapping and source frame are available

- **WHEN** the selected frame contains a source_video_frame
- **AND** frame mapping is verified
- **THEN** the system SHALL extract that exact video frame
- **AND** overlay the corresponding annotation-frame skeleton

#### Scenario: Mapping is unverified

- **WHEN** frame mapping is unverified
- **THEN** the system SHALL NOT guess a video frame
- **AND** the keyframe artifact SHALL be skipped with `frame_mapping_unverified`

### Requirement: Keyframe overlays remain factual

Annotated frames SHALL display COCO17 skeletons, objective geometry and metric values only.

#### Scenario: Body-axis overlay is generated

- **WHEN** body_axis_angle_deg is displayed
- **THEN** the reference SHALL be labelled screen horizontal
- **AND** the image MUST NOT label the angle as a water-surface angle

### Requirement: Skeleton overlays and trajectories share one resolver

The system SHALL reconstruct all skeleton midpoints (shoulder_mid, hip_mid, ankle_mid, trunk_mid, head_center) for both annotated keyframes and Cartesian trajectory charts using the same CanonicalKinematicFrame resolver as the side_2d_kinematics calculator.

#### Scenario: hip_mid is used in a keyframe and a trajectory chart

- **WHEN** hip_mid appears in an annotated keyframe and in body_posture.chart.hip_trajectory
- **THEN** both SHALL derive hip_mid from the same resolver output
- **AND** the renderer SHALL NOT independently reimplement bilateral midpoint or side-proxy fallback rules

### Requirement: Trajectory charts use body-relative coordinates from annotation geometry

Upper- and lower-limb Cartesian trajectories SHALL be reconstructed from the exact source revision of NormalizedAnnotation.keypoint_frames. AnnotationMetric.time_series remains authoritative for scalar metric charts, but is not required to contain joint-coordinate trajectories.

#### Scenario: Wrist trajectory is generated

- **WHEN** a wrist and its corresponding shoulder are available
- **THEN** the trajectory SHALL use wrist-minus-shoulder coordinates
- **AND** it SHALL prefer normalization by reference body length

#### Scenario: hip_mid trajectory is generated

- **WHEN** a hip_mid is available
- **THEN** the trajectory SHALL use hip_mid relative to the first valid hip_mid
- **AND** SHALL preserve its construction_mode

### Requirement: arm_extension_max frame uses per-side geometric derivation

The system SHALL select the arm-extension maximum keyframe from per-side geometric derivation rather than assuming a precomputed time series exists.

#### Scenario: Arm-extension maximum frame is selected

- **WHEN** upper_limb.keyframe.arm_extension_max is requested
- **THEN** the system SHALL select the frame with the maximum per-side wrist-to-shoulder distance normalized by reference body length
- **AND** SHALL record selected_side and selection_formula_id in artifact metadata
- **AND** SHALL NOT assume an arm_extension_ratio time_series exists

### Requirement: Mixed units are not placed on one axis

Motion ranges with different dimensions SHALL be rendered in separate panels or coordinate systems.

#### Scenario: ROM and vertical excursion are displayed

- **WHEN** joint ROM uses degrees
- **AND** vertical excursion uses pixels or body-length ratio
- **THEN** they MUST NOT share a single value axis

### Requirement: Radar chart is not a validated technical score

The radar chart title SHALL be exactly: `当前片段运动稳定性概览`

The radar chart SHALL contain a disclaimer stating that it is a within-clip visualization and not a validated composite technical score.

#### Scenario: Radar chart is generated

- **WHEN** stability display indices are available
- **THEN** the manifest SHALL record the source values and formula for each axis
- **AND** overall_score SHALL be null
- **AND** the system SHALL NOT classify the radar result as excellent, qualified or unqualified

#### Scenario: A radar axis is unavailable

- **WHEN** one axis lacks sufficient evidence
- **THEN** it SHALL be represented as N/A
- **AND** it MUST NOT be converted to numeric zero

#### Scenario: Lower-limb rhythm axis reads kick periodicity

- **WHEN** kick_periodicity value is present
- **THEN** the lower-limb axis SHALL read summary.kick_periodicity.value.score
- **AND** when value is null the axis SHALL render N/A

### Requirement: Generation is idempotent

The system SHALL return the existing artifact set when an identical generation is requested, and SHALL NOT create duplicate files or rows.

#### Scenario: Identical generation is requested twice

- **WHEN** annotation metric, source revision, metric hash, generator version and style profile are unchanged
- **AND** force is false
- **THEN** the system SHALL return the existing artifact set
- **AND** it SHALL NOT generate duplicate files or rows

### Requirement: Partial failure is preserved

The system SHALL preserve per-artifact failures and still mark the set ready or partial when other assets succeed.

#### Scenario: One frame fails to decode

- **WHEN** one annotated keyframe cannot be decoded
- **AND** other assets are generated successfully
- **THEN** the failed artifact SHALL contain `video_decode_failed`
- **AND** other artifacts SHALL remain ready
- **AND** the set status SHALL be partial

### Requirement: Public manifests do not expose local paths

The system SHALL serialize only relative storage paths in public API responses and SHALL NOT include absolute filesystem paths.

#### Scenario: Artifact manifest is returned

- **WHEN** the API serializes an artifact
- **THEN** storage_path SHALL be relative
- **AND** no absolute local filesystem path SHALL be included

### Requirement: Storage service returns checksum

The StorageService.save_bytes method SHALL return file size and SHA-256 checksum in addition to relative and absolute paths.

#### Scenario: A visual artifact is persisted

- **WHEN** the generator calls save_bytes with rendered image bytes
- **THEN** the returned dict SHALL include size_bytes and checksum_sha256
- **AND** the checksum SHALL be recorded on the artifact row

### Requirement: Head-motion spike keyframe uses reconstructed velocity

The system SHALL select the head-motion spike keyframe from detected spike candidates using reconstructed head-center vertical velocity, not an arbitrary head frame.

#### Scenario: Strongest detected spike is selected

- **WHEN** head_motion_spike_frames reports detected spike candidates
- **THEN** the system SHALL reconstruct head_center.y from canonical frames
- **AND** SHALL select the candidate with maximum absolute vertical velocity
- **AND** SHALL record the spike velocity and selection formula in artifact metadata

#### Scenario: No detected spike exists

- **WHEN** head_motion_spike_frames reports no candidates
- **THEN** the head-motion spike keyframe SHALL be skipped with `metric_unavailable`
- **AND** SHALL NOT fall back to an arbitrary head frame

### Requirement: Force regeneration is in-place and atomic

The system SHALL regenerate an existing ArtifactSet in place when force is true and the signature is unchanged, and SHALL NOT create a second ArtifactSet for the same signature.

#### Scenario: Force regeneration preserves prior assets on failure

- **WHEN** a force regeneration fails midway
- **THEN** the previous ready manifest and files SHALL remain usable
- **AND** new attempts SHALL be marked failed

#### Scenario: Files are replaced atomically

- **WHEN** a force regeneration finalizes successfully
- **THEN** final files SHALL be written via atomic replace
- **AND** obsolete artifact rows SHALL be removed only after finalization

### Requirement: Generation signature covers all inputs

The generation signature SHALL include source metric hash, source video checksum, style profile hash, stability-index config hash and artifact plan version, in addition to annotation metric id, source revision and generator version. The metric hash SHALL use canonical JSON serialization.

#### Scenario: Config or video change invalidates cache

- **WHEN** the source video file or stability-index config content changes
- **THEN** the generation signature SHALL change
- **AND** the system SHALL NOT return the previously cached artifact set

### Requirement: Storage rejects unsafe paths

The StorageService.save_bytes method SHALL reject absolute paths, parent-directory traversal, NUL characters and symlink escapes, and SHALL only write under the configured upload root.

#### Scenario: A traversal path is rejected

- **WHEN** save_bytes is called with a relative_path containing `..` or an absolute path
- **THEN** the system SHALL raise an unsafe storage path error
- **AND** SHALL NOT write any file

### Requirement: Radar index uses explicit executable formula

The radar display index SHALL be computed from an explicit, versioned configuration that defines per-axis input weights, direction, soft caps and minimum available inputs. Soft caps are visualization scaling only and SHALL NOT be treated as athlete performance thresholds.

#### Scenario: Fewer than three axes available

- **WHEN** fewer than three radar axes have sufficient evidence
- **THEN** the radar chart SHALL be skipped with `radar_inputs_insufficient`

#### Scenario: Three to four axes available

- **WHEN** three or four axes are available
- **THEN** the radar SHALL draw all five axes
- **AND** unavailable axes SHALL be labelled N/A and carry no plotted value
- **AND** the radar polygon SHALL NOT be filled

### Requirement: Manifest is an immutable snapshot of artifact rows

The persisted manifest SHALL be built from finalized artifact rows and treated as immutable after the set leaves the generating state. The system SHALL verify the manifest projection equals the stable ordering of artifact rows.

#### Scenario: Manifest matches artifact rows

- **WHEN** a generation finalizes
- **THEN** manifest.artifacts SHALL equal the stable sorted projection of artifact rows
- **AND** a manifest SHA-256 SHALL be persisted
