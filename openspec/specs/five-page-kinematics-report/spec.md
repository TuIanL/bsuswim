# five-page-kinematics-report Specification

## ADDED Requirements

### Requirement: The system assembles a fixed five-page kinematics report

The system SHALL assemble a `swim-report.v1` document using report profile
`side_2d_kinematics_5page_v1`.

The document SHALL contain exactly five sections with `page_number` values
`[1, 2, 3, 4, 5]`.

#### Scenario: Complete current inputs are available

- **GIVEN** a current `AnnotationMetric` with schema `swim-side-kinematics.v1`
- **AND** its current artifact set is available
- **AND** its current review finding set is available
- **WHEN** the report is assembled
- **THEN** the report SHALL contain exactly five sections
- **AND** their `page_number` values SHALL be `[1, 2, 3, 4, 5]`
- **AND** the report `assembly_status` SHALL be `ready`

### Requirement: Report-page module keys are profile-specific

For report profile `side_2d_kinematics_5page_v1`, `section.module_key` SHALL
identify the report-page aggregation module.

It SHALL NOT be interpreted as an artifact `module_key` or a legacy
`side_technical` section key.

Each section SHALL declare `source_module_keys`, and each asset SHALL retain its
original artifact `module_key`.

#### Scenario: Page two declares aggregation and source modules

- **WHEN** page 2 (`body_posture_control`) is assembled
- **THEN** `section.module_key` SHALL be `body_posture_head_trunk`
- **AND** `section.source_module_keys` SHALL be `["body_posture", "head_trunk"]`
- **AND** each included asset SHALL retain its own artifact `module_key` of
  `body_posture` or `head_trunk`

#### Scenario: Two report profiles are independent

- **GIVEN** report profile `side_technical` uses section keys
  `body_position` / `arm_entry` / `catch_pull` / `leg_kick` / `efficiency`
- **AND** report profile `side_2d_kinematics_5page_v1` uses page types
  `overview` / `body_posture_head_trunk` / `upper_limb` / `lower_limb` /
  `review_summary`
- **THEN** the two profiles SHALL be treated as independent, non-aliased
  report profiles

### Requirement: Each section carries explicit pagination semantics

Each report section SHALL contain `page_number`, `page_type`, `module_key`,
`source_module_keys`, `assets`, `metrics`, `findings`, and `quality_notes`.

#### Scenario: A section has no available data

- **WHEN** a required module has no usable metric
- **THEN** its section SHALL still exist
- **AND** its `status` SHALL be `unavailable`
- **AND** its `metrics`, `assets`, and `findings` SHALL be empty arrays
- **AND** its `quality_notes` SHALL explain why the module is unavailable

### Requirement: Page one describes the analysis input and boundaries

Page 1 (`analysis_overview`) SHALL summarize the analysis inputs, quality status
and explicit analysis boundaries before any technical metrics are shown.

#### Scenario: Overview page is assembled

- **WHEN** the report is assembled
- **THEN** page 1 SHALL include athlete and session information
- **AND** video and annotation information
- **AND** effective-frame and joint-completeness information
- **AND** quality status and available modules
- **AND** explicit analysis-boundary statements

### Requirement: Pages two through four are category based

Pages 2, 3 and 4 SHALL group content by analysis module category: page 2 covers
`body_posture` and `head_trunk`, page 3 covers `upper_limb`, page 4 covers
`lower_limb`, each drawing metrics, assets and findings from its category.

#### Scenario: Body and head-trunk data are available

- **THEN** page 2 SHALL contain `body_posture` and `head_trunk`
  metrics, assets and findings

#### Scenario: Upper-limb data are available

- **THEN** page 3 SHALL contain `upper_limb` metrics, assets and findings

#### Scenario: Lower-limb data are available

- **THEN** page 4 SHALL contain `lower_limb` metrics, assets and findings

### Requirement: Page five remains a review page

The system SHALL NOT transform a review finding into a deterministic diagnosis
or training prescription.

#### Scenario: Review findings are present

- **WHEN** page 5 is assembled
- **THEN** every included finding SHALL retain `status = review_required`
- **AND** the page SHALL retain evidence metrics, evidence frames,
  confidence, limitations and review question
- **AND** the system SHALL NOT add strength, propulsion or training-cause claims
- **AND** `next_capture_suggestions` SHALL contain only data-acquisition
  suggestions, never training prescriptions

### Requirement: Radar semantics are passed through from the artifact manifest

The system SHALL read radar semantics, including the disclaimer, from the
current `KinematicArtifactSet.manifest` and pass it through to page 5.

#### Scenario: Radar artifact present

- **WHEN** the current artifact set includes a radar artifact
- **THEN** page 5 SHALL include `content.radar_semantics` from the manifest
- **AND** the report layer SHALL NOT hardcode the disclaimer string

#### Scenario: Radar artifact missing

- **WHEN** the current artifact set exists but has no radar asset
- **THEN** `content.radar_semantics` SHALL still be passed through if present
- **AND** no radar asset SHALL appear in page 5 `assets`
- **AND** `quality_notes` SHALL record the radar asset as unavailable

#### Scenario: Entire artifact set missing

- **WHEN** no current artifact set exists
- **THEN** `content.radar_semantics` SHALL be `null`
- **AND** the report layer SHALL NOT construct a default disclaimer

### Requirement: Current source products are resolved by their own expected signature

The artifact set and the review finding set SHALL each be resolved through their
own expected-signature resolver. The two signature formulas SHALL remain
independent.

#### Scenario: An older artifact set exists

- **GIVEN** an artifact set exists for the annotation metric
- **BUT** its generation signature is not the current expected artifact signature
- **WHEN** the report is assembled
- **THEN** the artifact set MUST NOT be used
- **AND** the report `assembly_status` SHALL be `partial` with a structured warning

#### Scenario: An older finding set exists

- **GIVEN** a review finding set exists for the annotation metric
- **BUT** its generation signature is not the current expected finding signature
- **WHEN** the report is assembled
- **THEN** the finding set MUST NOT be used
- **AND** the report SHALL be `partial` with a structured warning

### Requirement: Stale metrics block report assembly

The system SHALL reject report assembly when the `AnnotationMetric` is stale
relative to its `NormalizedAnnotation` revision.

#### Scenario: Annotation revision changed

- **GIVEN** `annotation_metric.source_revision` differs from
  `normalized_annotation.revision`
- **WHEN** report assembly is requested
- **THEN** the system SHALL return `409 metric_revision_stale`
- **AND** SHALL NOT assemble a report using the stale metric

### Requirement: Missing optional source products degrade gracefully

The system SHALL still produce all five pages with `assembly_status = partial`
and a structured warning when an optional input (artifact set or review finding
set) is absent, rather than failing. The report SHALL NOT be blocked by the
absence of an optional product.

#### Scenario: Artifacts are not generated

- **GIVEN** the current metric is valid
- **AND** no current artifact set exists
- **WHEN** the report is assembled
- **THEN** the report SHALL still contain five sections
- **AND** its `assembly_status` SHALL be `partial`
- **AND** its warnings SHALL include `artifacts_not_generated`

#### Scenario: Review findings are not generated

- **GIVEN** the current metric is valid
- **AND** no current review finding set exists
- **WHEN** the report is assembled
- **THEN** the report SHALL still contain five sections
- **AND** its `assembly_status` SHALL be `partial`
- **AND** its warnings SHALL include `review_findings_not_generated`

### Requirement: Generated empty findings are valid

A current ready review finding set with an empty findings list SHALL be treated
as a valid, fully-generated input, not as "findings not generated".

#### Scenario: Rules ran but matched no findings

- **GIVEN** a current ready review finding set exists
- **AND** its findings list is empty
- **WHEN** the report is assembled
- **THEN** the finding input SHALL be considered ready
- **AND** the report SHALL NOT emit `review_findings_not_generated`

### Requirement: The report is reproducible and traceable

The system SHALL produce identical reports given identical current source
products and the same report profile. The report assembly MUST be deterministic
for a fixed set of inputs, producing identical generation signatures and source
traces.

#### Scenario: The same inputs are assembled twice

- **WHEN** identical current source products and the same report profile
  are assembled twice
- **THEN** both reports SHALL have the same generation signature
- **AND** their source trace SHALL reference the same source IDs,
  revisions, hashes and signatures

### Requirement: Report metric display values come from one index

All pages SHALL consume `ReportMetric` objects from a single immutable
`all_report_metrics` index built before any page is assembled.

#### Scenario: Page builders do not re-read raw envelopes

- **WHEN** pages 2 through 5 are assembled
- **THEN** they SHALL read display values from the shared `all_report_metrics`
- **AND** SHALL NOT re-read raw `summary` envelopes for display values
- **AND** retest metrics on page 5 SHALL use the same values as pages 2-4

### Requirement: Report assembly status is distinct from upstream status

The top-level report SHALL expose `assembly_status` (`ready` / `partial`),
separate from `artifact_set.status` and `finding_set.status`.

#### Scenario: Upstream partial does not overwrite report semantics

- **GIVEN** `artifact_set.status` is `partial`
- **WHEN** the report is assembled
- **THEN** the report layer SHALL preserve `artifact_set.status = partial`
  in `source_trace`
- **AND** the report `assembly_status` SHALL be derived independently
- **AND** the report layer SHALL NOT reinterpret `artifact_set.status` as
  `section.status`

### Requirement: Page one overview stats are separate from canonical metrics

The system SHALL build page 1 (`analysis_overview`) coverage statistics
(`effective_frame_count`, `joint_completeness_ratio`, available-module counts)
via a dedicated `overview_stats` structure, NOT through the canonical metric
registry `KINEMATICS_REPORT_METRICS`.

#### Scenario: Overview stats use a separate model

- **WHEN** page 1 is assembled
- **THEN** coverage statistics SHALL be represented as `ReportOverviewStat`
  entries with a `source` of `normalized_annotation`, `metric_quality`, or
  `report_assembly`
- **AND** none of these keys SHALL be added to `KINEMATICS_REPORT_METRICS`
- **AND** kinematic metric display values SHALL still come from `all_report_metrics`

### Requirement: Artifact resolver resolves by expected signature and reports status

The artifact resolver SHALL resolve the current artifact set by its own expected
signature and SHALL return a structured resolution result with a
`resolution_status`.

#### Scenario: Ready artifact set is consumed

- **GIVEN** a current artifact set with `status = ready` matching the expected signature
- **WHEN** the report is assembled
- **THEN** the resolver SHALL return `resolution_status = current_ready`
- **AND** the artifacts SHALL be projected into the report

#### Scenario: Partial, generating or failed artifact set degrades the report

- **GIVEN** a current artifact set matching the expected signature but with
  `status` of `partial`, `generating`, or `failed`
- **WHEN** the report is assembled
- **THEN** the resolver SHALL return the corresponding `resolution_status`
- **AND** the report `assembly_status` SHALL be `partial`
- **AND** `generating`/`failed` SHALL NOT project any artifact assets

#### Scenario: No current artifact set exists

- **GIVEN** no artifact set matches the expected signature
- **WHEN** the report is assembled
- **THEN** the resolver SHALL return `resolution_status = not_generated`
- **AND** the report `assembly_status` SHALL be `partial`

### Requirement: Retest metrics resolve finding evidence to canonical keys

`retest_metrics` on page 5 SHALL resolve each `FindingEvidenceMetric` to canonical
metric keys via `source_metric_keys` / `derivation`, and SHALL NOT assume
`finding.evidence_metrics[].key` is itself a canonical metric key.

#### Scenario: Derived finding key maps to a canonical metric

- **GIVEN** a finding evidence metric with key `hip_vertical_range_ratio`
  and `source_metric_keys = ["hip_vertical_range_px"]`
- **WHEN** retest metrics are built
- **THEN** the retest entry SHALL use `metric_key = hip_vertical_range_px`
- **AND** SHALL preserve `trigger_metric_key = hip_vertical_range_ratio`
  and the `derivation`
- **AND** the displayed value SHALL come from `all_report_metrics`

### Requirement: Section readiness follows an explicit policy

The system SHALL derive each technical section's `status`
(`ready` / `partial` / `unavailable`) from `PAGE_READINESS_POLICY`, not from
implementer discretion.

#### Scenario: Missing required metric group marks the page unavailable

- **GIVEN** page 3 (`upper_limb_kinematics`) has no available
  `left_elbow_angle_deg` or `right_elbow_angle_deg`
- **WHEN** the report is assembled
- **THEN** page 3 `status` SHALL be `unavailable`

#### Scenario: Missing preferred asset marks the page partial

- **GIVEN** page 3 has available elbow metrics but no
  `upper_limb.chart.elbow_angle_timeseries` asset
- **WHEN** the report is assembled
- **THEN** page 3 `status` SHALL be `partial`

### Requirement: A persisted three-layer report fixture is available

The system tests SHALL provide a fixture factory that builds a persisted
`TrainingSession` → `SessionVideo` → `NormalizedAnnotation` → `AnnotationMetric`
with its current `KinematicArtifactSet` and `KinematicReviewFindingSet`, using
real calculator and generation services rather than hand-written JSON.

#### Scenario: Complete fixture is built

- **WHEN** the fixture factory is invoked with default options
- **THEN** it SHALL produce a persisted metric, a current artifact set, and a
  current review finding set for the same `annotation_metric_id`

#### Scenario: Fixture variants are supported

- **WHEN** the fixture factory is invoked with `with_artifacts=False` or
  `with_findings=False`
- **THEN** it SHALL produce a valid metric with the corresponding optional
  product absent, for partial-report testing

#### Scenario: Fixture ownership allows finding generation

- **WHEN** the fixture factory builds the persisted objects
- **THEN** `session.coach_id` SHALL equal the fixture `user.id`
- **AND** `generate_review_findings()` ownership validation
  (`session.coach_id == current_user.id`) SHALL succeed on the fixture
