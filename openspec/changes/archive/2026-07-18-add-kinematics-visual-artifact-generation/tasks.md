# Tasks: add-kinematics-visual-artifact-generation

## 0. Baseline and fixtures

- [x] 0.1 Run current backend tests and record baseline
- [x] 0.2 Reuse the synthetic side_2d_kinematics fixture
- [x] 0.3 Add an in-memory fake video-frame extractor for tests
- [x] 0.4 Add a deterministic blank-frame fixture with known dimensions
- [x] 0.5 Record current side_2d_kinematics manifest input shape
- [x] 0.6 Add regression test proving metric results are not mutated

## 1. Artifact contracts

- [x] 1.1 Define artifact schema version `swim-kinematic-artifacts.v1`
- [x] 1.2 Define artifact type constants
- [x] 1.3 Define artifact status and set status enums
- [x] 1.4 Define structured skip/error reason codes
- [x] 1.5 Add `ArtifactPresentation` schema
- [x] 1.6 Add `KinematicArtifactRead` schema
- [x] 1.7 Add `KinematicArtifactSetRead` schema
- [x] 1.8 Ensure API entries flatten source revision and generator version
- [x] 1.9 Prohibit absolute paths in public schemas

## 2. Database model and migration

- [x] 2.1 Add `KinematicArtifactSet` model
- [x] 2.2 Add `KinematicArtifact` model
- [x] 2.3 Add ArtifactSet → Artifact relationship
- [x] 2.4 Add unique generation signature constraint
- [x] 2.5 Add unique artifact_key per set constraint
- [x] 2.6 Add cascade behavior
- [x] 2.7 Register models in models/__init__.py
- [x] 2.8 Add Alembic migration 0009
- [x] 2.9 Add migration downgrade

## 3. Generation context and preflight

- [x] 3.1 Resolve AnnotationMetric by exact id
- [x] 3.2 Resolve NormalizedAnnotation from AnnotationMetric
- [x] 3.3 Resolve SessionVideo and VideoFile
- [x] 3.4 Reuse ownership validation through normalized annotation
- [x] 3.5 Require calculator `side_2d_kinematics`
- [x] 3.6 Require schema `swim-side-kinematics.v1`
- [x] 3.7 Reject null source_revision
- [x] 3.8 Reject stale source_revision
- [x] 3.9 Calculate source metric SHA-256 via canonical JSON (sort_keys, no NaN)
- [x] 3.10 Read source video checksum from VideoFile.checksum_sha256
- [x] 3.11 Read style profile and stability-index config content hashes
- [x] 3.12 Calculate deterministic generation signature over all inputs
- [x] 3.13 Test equivalent dict key ordering produces the same signature

## 4. Artifact planning

- [x] 4.1 Define stable ArtifactPlanItem
- [x] 4.2 Define all artifact keys centrally
- [x] 4.3 Map artifact keys to module_key and metric_keys
- [x] 4.4 Add required-input predicates per artifact
- [x] 4.5 Mark unsupported items skipped instead of raising globally
- [x] 4.6 Limit planned annotated keyframes to 12
- [x] 4.7 Produce deterministic artifact ordering

## 5. Frame selection

- [x] 5.1 Implement min/max time-series selection
- [x] 5.2 Use confidence as tie-breaker
- [x] 5.3 Use earliest frame as final deterministic tie-breaker
- [x] 5.4 Select body-axis min/max frames
- [x] 5.5 Select left/right elbow min/max frames
- [x] 5.6 Select left/right knee min/max frames
- [x] 5.7 Select strongest head-motion spike frame
- [x] 5.8 Select arm-extension maximum by per-side wrist-to-shoulder distance / reference body length
- [x] 5.9 Record selected side and formula id in artifact metadata
- [x] 5.10 Fall back to representative_frames when required
- [x] 5.11 Preserve annotation and source-video frame ids
- [x] 5.12 Reconstruct head-center vertical velocity for detected spike candidates
- [x] 5.13 Select the detected spike with maximum absolute vertical velocity
- [x] 5.14 Record spike velocity and selection formula in artifact metadata
- [x] 5.15 Skip the artifact when no detected spike exists (skip_reason metric_unavailable)

## 6. Video frame extraction

- [x] 6.1 Add `VideoFrameExtractor` protocol
- [x] 6.2 Add OpenCV implementation
- [x] 6.3 Validate source video path
- [x] 6.4 Require verified source-frame mapping
- [x] 6.5 Extract frames in sorted order
- [x] 6.6 Cache duplicate source-frame extractions
- [x] 6.7 Validate decoded frame number
- [x] 6.8 Return structured decode errors (requested_frame, decoded_frame, exact_match)
- [x] 6.9 Do not load the whole video into memory
- [x] 6.10 Mark frame failed when exact_match is false
- [x] 6.11 Add keyframe-interval test video proving exact-frame extraction

## 7. Coordinate transformation and cropping

- [x] 7.1 Build canonical frames via `KinematicFrameSequenceProvider`
- [x] 7.2 Verify provider output matches calculator canonical frames
- [x] 7.3 Validate pixel coordinate system
- [x] 7.4 Detect coordinates outside video bounds
- [x] 7.5 Add skeleton bbox calculation
- [x] 7.6 Add 15% crop margin
- [x] 7.7 Preserve output aspect ratio
- [x] 7.8 Transform points after crop and resize
- [x] 7.9 Refuse unverified coordinate-space scaling

## 8. Annotated keyframe renderer

- [x] 8.1 Add COCO17 edge map
- [x] 8.2 Render visibility-aware joints
- [x] 8.3 Render skeleton connections
- [x] 8.4 Render shoulder-to-ankle body axis
- [x] 8.5 Render screen-horizontal reference
- [x] 8.6 Render elbow-angle arc
- [x] 8.7 Render knee-angle arc
- [x] 8.8 Render metric value and reference basis
- [x] 8.9 Export 1600×900 PNG
- [x] 8.10 Return dimensions, size and checksum

## 9. Time-series chart renderer

- [x] 9.1 Configure Matplotlib Agg
- [x] 9.2 Add deterministic style profile
- [x] 9.3 Implement body angle chart
- [x] 9.4 Implement left/right elbow chart
- [x] 9.5 Implement left/right knee chart
- [x] 9.6 Show annotation/source frame basis
- [x] 9.7 Handle gaps without connecting missing intervals
- [x] 9.8 Downsample display data to at most 600 points
- [x] 9.9 Export SVG with viewBox/width/height (logical css_px)

## 10. Annotation-derived trajectory renderer

- [x] 10.1 Consume `KinematicFrameSequenceProvider` (defined in §7)
- [x] 10.2 Reuse the existing `CanonicalKinematicFrame` resolver (`resolve_frames`)
- [x] 10.3 Build left/right wrist trajectories relative to same-side shoulder
- [x] 10.4 Build left/right elbow trajectories relative to same-side shoulder
- [x] 10.5 Build hip_mid trajectory relative to the first valid hip_mid
- [x] 10.6 Preserve hip_mid construction_mode and fallback ranges
- [x] 10.7 Build left/right knee trajectories relative to hip_mid
- [x] 10.8 Build left/right ankle trajectories relative to hip_mid
- [x] 10.9 Prefer reference-body-length normalization
- [x] 10.10 Fall back to pixel units with structured warning
- [x] 10.11 Convert display y-axis to upward-positive
- [x] 10.12 Preserve missing-data and construction-mode discontinuities
- [x] 10.13 Do not connect left_proxy and right_proxy segments
- [x] 10.14 Downsample only after trajectory derivation
- [x] 10.15 Export SVG with viewBox/width/height

## 11. Range comparison chart

- [x] 11.1 Extract left/right elbow ROM
- [x] 11.2 Extract left/right knee ROM
- [x] 11.3 Extract head and hip vertical excursion
- [x] 11.4 Extract body-axis angle range
- [x] 11.5 Render joint-ROM degree panel
- [x] 11.6 Render vertical-excursion panel
- [x] 11.7 Render body-angle-range panel
- [x] 11.8 Never mix px, ratio and deg on one axis
- [x] 11.9 Export SVG

## 12. Stability radar

- [x] 12.1 Define exact formula and scaling parameters for every radar axis (YAML)
- [x] 12.2 Implement weight renormalization for partially available inputs
- [x] 12.3 Implement body-posture display index
- [x] 12.4 Implement upper-limb display index
- [x] 12.5 Implement lower-limb rhythm display index (read `summary.kick_periodicity.value.score`)
- [x] 12.6 Implement head-control display index
- [x] 12.7 Implement data-completeness index
- [x] 12.8 Preserve raw evidence and formula id per axis
- [x] 12.9 Render unavailable axes as N/A, not zero
- [x] 12.10 Skip radar when fewer than three axes are available
- [x] 12.11 Do not fill the radar polygon when any axis is unavailable
- [x] 12.12 Use exact title `当前片段运动稳定性概览`
- [x] 12.13 Include non-validated-score disclaimer
- [x] 12.14 Do not calculate an overall radar score
- [x] 12.15 Test config changes alter generation signature
- [x] 12.12 Export SVG

## 13. Storage and manifest

- [x] 13.1 Extend StorageService.save_bytes with SHA-256 and mime_type
- [x] 13.2 Validate nested relative paths (reject absolute, `..`, NUL, symlink escape)
- [x] 13.3 Add generic public storage URL builder
- [x] 13.4 Store only relative paths in database
- [x] 13.5 Add generation-signature directory layout
- [x] 13.6 Persist ready/skipped/failed artifact rows
- [x] 13.7 Build flattened manifest response
- [x] 13.8 Snapshot render specs and selected raw values
- [x] 13.9 Never expose absolute filesystem paths
- [x] 13.10 Persist manifest SHA-256
- [x] 13.11 Define Artifact rows as generation-time source of truth
- [x] 13.12 Build immutable manifest snapshot during finalization
- [x] 13.13 Verify manifest projection matches persisted artifact rows

## 14. Generation service

- [x] 14.1 Add KinematicArtifactGenerationService
- [x] 14.2 Implement generating → ready transition
- [x] 14.3 Implement generating → partial transition
- [x] 14.4 Implement generating → failed transition
- [x] 14.5 Return existing set for identical signature
- [x] 14.6 Define force regeneration as in-place ArtifactSet regeneration (no new Set)
- [x] 14.7 Lock the existing ArtifactSet during force regeneration (FOR UPDATE)
- [x] 14.8 Render to temporary files and atomically replace final files (os.replace)
- [x] 14.9 Preserve the previous ready manifest until regeneration finalization
- [x] 14.10 Remove obsolete artifact rows and files after successful finalization
- [x] 14.11 Reject concurrent generation with 409
- [x] 14.12 Run CPU render work in a threadpool
- [x] 14.13 Ensure one artifact failure does not abort other artifacts
- [x] 14.14 Persist systemic failure information

## 15. API

- [x] 15.1 Add POST annotation-metrics/{id}/artifacts/generate
- [x] 15.2 Add GET annotation-metrics/{id}/artifacts
- [x] 15.3 Add force query parameter
- [x] 15.4 Add structured unsupported-schema error
- [x] 15.5 Add structured stale-revision error
- [x] 15.6 Add generation-in-progress conflict
- [x] 15.7 Return 201 for a new set
- [x] 15.8 Return 200 for an existing or regenerated set
- [x] 15.9 Register artifact router
- [x] 15.10 Exclude absolute paths from API response

## 16. Report compatibility projection

- [x] 16.1 Add artifact-to-report-asset projection helper
- [x] 16.2 Map annotated frames to ReportAsset.annotated_frame
- [x] 16.3 Map SVG charts to ReportAsset.image
- [x] 16.4 Preserve title, label, value and caption
- [x] 16.5 Do not wire the helper into ReportBuilder in this Change

## 17. Tests

- [x] 17.1 Test exact AnnotationMetric resolution
- [x] 17.2 Test unsupported calculator/schema
- [x] 17.3 Test stale revision blocks generation
- [x] 17.4 Test unknown revision blocks generation
- [x] 17.5 Test unverified mapping creates partial set
- [x] 17.6 Test chart generation without video
- [x] 17.7 Test deterministic frame selection
- [x] 17.8 Test duplicate frames are decoded once
- [x] 17.9 Test coordinate-space mismatch
- [x] 17.10 Test visibility-aware skeleton rendering
- [x] 17.11 Test angle arc rendering
- [x] 17.12 Test SVG output contains no NaN/Inf
- [x] 17.13 Test time-series gaps remain gaps
- [x] 17.14 Test trajectory coordinate normalization
- [x] 17.15 Test mixed units are split into panels
- [x] 17.16 Test exact radar title
- [x] 17.17 Test radar contains disclaimer and no overall score
- [x] 17.18 Test unavailable radar axis is N/A
- [x] 17.19 Test manifest fields and relative URLs
- [x] 17.20 Test idempotent generation
- [x] 17.21 Test force regeneration
- [x] 17.22 Test generation-in-progress conflict
- [x] 17.23 Test partial and failed statuses
- [x] 17.24 Test artifact-to-report projection
- [x] 17.25 Test legacy metrics and PDF tests remain passing
- [x] 17.26 Test hip_mid trajectory uses the shared canonical resolver
- [x] 17.27 Test renderer does not duplicate midpoint construction logic
- [x] 17.28 Test bilateral → proxy mode transition creates a visible gap
- [x] 17.29 Test arm-extension frame selection records the correct side
- [x] 17.30 Test kick periodicity radar reads `value.score`
- [x] 17.31 Test absent kick periodicity value renders N/A

## 18. Documentation and OpenSpec

- [x] 18.1 Add kinematics-visual-artifacts capability spec
- [x] 18.2 Amend backend-platform-core storage/API capability
- [x] 18.3 Document all artifact keys
- [x] 18.4 Document radar display-index formulas
- [x] 18.5 Document frame-mapping requirements
- [x] 18.6 Document supported image and chart formats
- [x] 18.7 Run `openspec validate add-kinematics-visual-artifact-generation --strict`
