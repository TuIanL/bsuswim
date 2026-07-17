## 0. Early fixtures and contract tests

- [x] 0.1 Run current backend metrics tests and record baseline
- [x] 0.2 Add regression test proving legacy side_view_metrics remains callable
- [x] 0.3 Add a deterministic synthetic kinematics sequence generator (≥96 frames)
- [x] 0.4 Generator includes bilateral, left-only, right-only, occluded, estimated, missing frames
- [x] 0.5 Synthetic data includes known left/right kick lag and dominant period
- [x] 0.6 Produce a normalized real-CVAT golden fixture (40–80 frames)
- [x] 0.7 Verify fixture contains COCO17 visibility and frame mapping metadata
- [x] 0.8 Add tests that reject mixing left_proxy and right_proxy in one temporal series

## 1. Schema and model

- [x] 1.1 Add `MetricEnvelope` schema
- [x] 1.2 Add `KinematicSeriesPoint` schema
- [x] 1.3 Add `MetricRange` schema
- [x] 1.4 Add `RepresentativeFrame` schema
- [x] 1.5 Add `Side2DKinematicsResult` schema
- [x] 1.6 Add `ReferenceBodyLength` quality object schema
- [x] 1.7 Define top-level Side2DKinematicsResult with source, reference_body_length, summary, time_series, ranges, representative_frames, quality
- [x] 1.8 Define MetricProvenance with frame_basis and mapping_status
- [x] 1.9 Define MetricSourceInfo with revision_status (not persisted)
- [x] 1.10 Use Field(default_factory=dict/list) for all mutable fields
- [x] 1.7 Define `swim-side-kinematics.v1` constants
- [x] 1.8 Add `side_2d_kinematics` and `1.0.0` calculator constants
- [x] 1.9 Add `source_revision` column to AnnotationMetric model
- [x] 1.10 Add Alembic migration for source_revision
- [x] 1.11 Persist actual schema_version on upsert (not model default)

## 2. Calculator registry and service routing

- [x] 2.1 Add calculator registry with AbstractMetricCalculator protocol
- [x] 2.2 Register legacy `side_view_metrics` calculator
- [x] 2.3 Register new `side_2d_kinematics` calculator
- [x] 2.4 Extend `calculate_and_persist()` with calculator argument
- [x] 2.5 Include normalized_annotation id and revision in calculation context
- [x] 2.6 UPSERT refreshes source_revision, schema_version, metrics, quality, updated_at
- [x] 2.7 Filter metric reads by calculator name
- [x] 2.8 Order latest records by updated_at DESC

## 3. CanonicalKinematicFrame resolver

- [x] 3.1 Add PointSample with visibility-derived confidence
- [x] 3.2 Resolve all 17 COCO17 keypoint names from KeypointFrame
- [x] 3.3 Build shoulder_mid with construction_mode
- [x] 3.4 Build hip_mid with construction_mode
- [x] 3.5 Build ankle_mid with construction_mode
- [x] 3.6 Build trunk_mid with construction_mode
- [x] 3.7 Build head_center with construction_mode
- [x] 3.8 Add single-side fallback behavior (confidence × 0.5, SINGLE_SIDE_FALLBACK)
- [x] 3.9 Calculate median reference_body_length_px with quality envelope
- [x] 3.10 Preserve annotation_frame and source_video_frame provenance
- [x] 3.11 Prevent construction_mode switching in temporal metrics

## 4. Geometry and statistics utilities

- [x] 4.1 Add `line_angle_to_screen_horizontal_deg()` (0–90°)
- [x] 4.2 Add `signed_line_tilt_deg()` ([-90°, 90°))
- [x] 4.3 Do not modify existing `angle_to_horizontal()`
- [x] 4.4 Add vector and midpoint helpers
- [x] 4.5 Add percentile and robust P95−P05 ROM helpers
- [x] 4.6 Add standard deviation and CV helpers (guard mean < 1°)
- [x] 4.7 Add Pearson correlation helper
- [x] 4.8 Add autocorrelation helper
- [x] 4.9 Add cross-correlation lag helper
- [x] 4.10 Add MAD velocity spike detector
- [x] 4.11 Ensure helpers never return NaN or Inf

## 5. Continuity

- [x] 5.1 Define expected_frame_step from verified frame mapping
- [x] 5.2 Implement delta-metric continuity factor
- [x] 5.3 Implement longest-contiguous-run factor for sequence metrics
- [x] 5.4 Do not apply continuity penalties to independent per-frame summaries

## 6. Body posture metrics

- [x] 6.1 Implement torso_axis_angle_deg time series
- [x] 6.2 Implement body_axis_angle_deg time series
- [x] 6.3 Implement hip_vertical_range_px
- [x] 6.4 Implement shoulder_vertical_range_px
- [x] 6.5 Implement body_angle_std_deg
- [x] 6.6 Implement posture_stability_cv (guard mean < 1°)
- [x] 6.7 Select body posture representative frames
- [x] 6.8 Populate ranges and provenance

## 7. Upper-limb metrics

- [x] 7.1 Implement left_elbow_angle_deg
- [x] 7.2 Implement right_elbow_angle_deg
- [x] 7.3 Implement robust elbow_rom_deg (P95−P05)
- [x] 7.4 Implement normalized wrist_trajectory
- [x] 7.5 Implement arm_extension_ratio
- [x] 7.6 Implement wrist_velocity_px_per_frame
- [x] 7.7 Select left/right elbow representative frames
- [x] 7.8 Degrade one-side-only calculations correctly

## 8. Lower-limb metrics

- [x] 8.1 Implement left_knee_angle_deg
- [x] 8.2 Implement right_knee_angle_deg
- [x] 8.3 Implement robust knee_rom_deg (P95−P05)
- [x] 8.4 Implement relative ankle_vertical_range_px
- [x] 8.5 Implement kick_periodicity (autocorrelation, stroke-aware)
- [x] 8.6 Implement left_right_kick_timing (cross-correlation)
- [x] 8.7 Select left/right knee representative frames
- [x] 8.8 Handle insufficient-cycle quality for periodicity

## 9. Head and trunk metrics

- [x] 9.1 Implement head_vertical_range_px
- [x] 9.2 Implement head_shoulder_relative_offset
- [x] 9.3 Implement head_body_synchrony (Pearson correlation)
- [x] 9.4 Implement head_motion_spike_frames (MAD robust z-score)
- [x] 9.5 Implement trunk_vertical_stability (detrended residual std)
- [x] 9.6 Select head/trunk representative frames
- [x] 9.7 Handle nose-only and partial-head fallbacks

## 10. Confidence, availability and quality

- [x] 10.1 Implement per-point visibility weights (visible=1.0, occluded=0.7, estimated=0.5)
- [x] 10.2 Implement per-frame confidence (geom_mean of required points)
- [x] 10.3 Implement per-metric summary confidence
- [x] 10.4 Implement sample_factor, continuity_factor, mapping_factor
- [x] 10.5 Populate availability in every MetricEnvelope
- [x] 10.6 Implement Side2DKinematicsQualityEvaluator
- [x] 10.7 Do not emit missing scale/waterline/event warnings
- [x] 10.8 Ensure every canonical metric key exists when unavailable
- [x] 10.9 Add METRIC_SAMPLE_INSUFFICIENT, SINGLE_SIDE_FALLBACK issue codes

## 11. API

- [x] 11.1 Add calculator query parameter to calculate-metrics endpoint
- [x] 11.2 Validate calculator names against registry
- [x] 11.3 Return 422 for non-side view annotations
- [x] 11.4 Return 422 when no usable skeleton frames exist
- [x] 11.5 Return degraded 200 for partial point availability
- [x] 11.6 Extend existing GET /normalized-annotations/{id}/metrics with calculator (default: side_view_metrics) and calculator_version params
- [x] 11.7 Add unsupported_metric_calculator structured error (422)
- [x] 11.8 Return source_revision and revision_status
- [x] 11.9 Test old POST and GET calls without calculator parameters

## 12. Tests

- [x] 12.1 Test acute horizontal angles for both swim directions
- [x] 12.2 Test signed tilt angle for four quadrants
- [x] 12.3 Test COCO17 left/right key resolution
- [x] 12.4 Test bilateral midpoint calculation
- [x] 12.5 Test single-side fallback and confidence reduction
- [x] 12.6 Test construction_mode not mixed in temporal series
- [x] 12.7 Test missing/occluded/estimated points
- [x] 12.8 Test reference_body_length quality propagation
- [x] 12.9 Test all body posture metrics on synthetic data
- [x] 12.10 Test all upper-limb metrics on synthetic data
- [x] 12.11 Test all lower-limb metrics on synthetic data
- [x] 12.12 Test all head/trunk metrics on synthetic data
- [x] 12.13 Test periodicity using synthetic sinusoidal ankle sequence
- [x] 12.14 Test left/right lag with known phase offset
- [x] 12.15 Test representative frame provenance and extractable flag
- [x] 12.16 Test schema always contains all canonical metric keys
- [x] 12.17 Test no NaN/Inf appears in JSON output
- [x] 12.18 Test persistence and source_revision update
- [x] 12.19 Test calculator-filtered metric reads
- [x] 12.20 Test revision_status tri-state (current/stale/unknown)
- [x] 12.21 Test legacy side_view_metrics regression
- [x] 12.22 Test real CVAT golden fixture produces expected output shape

## 13. Migration

- [x] 13.1 Add Alembic migration for source_revision column
- [x] 13.2 Add migration downgrade
- [x] 13.3 Verify existing AnnotationMetric rows remain readable with source_revision=NULL
- [x] 13.4 No other database schema changes

## 14. OpenSpec

- [x] 14.1 Add side-2d-kinematics capability spec (done)
- [x] 14.2 Amend side-view-metrics API capability (done)
- [x] 14.3 Amend backend-platform-core capability (done)
- [x] 14.4 `openspec validate add-side-2d-kinematics-metrics --strict`
