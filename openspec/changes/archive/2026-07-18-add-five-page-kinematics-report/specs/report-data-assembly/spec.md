# report-data-assembly Specification

## ADDED Requirements

### Requirement: Five-page kinematics report profile is supported

The system SHALL support report profile `side_2d_kinematics_5page_v1` in addition
to the existing `side_technical` profile.

The `side_2d_kinematics_5page_v1` profile SHALL assemble exactly five pages from
`AnnotationMetric(swim-side-kinematics.v1)`, the current
`KinematicArtifactSet`, and the current `KinematicReviewFindingSet`, without
depending on `AnalysisResult.diagnostics`.

#### Scenario: Five-page profile uses its own page types

- **WHEN** report profile `side_2d_kinematics_5page_v1` is assembled
- **THEN** sections SHALL use page types
  `overview` / `body_posture_control` / `upper_limb_kinematics` /
  `lower_limb_kinematics` / `review_and_retest`
- **AND** the legacy `side_technical` section keys SHALL NOT be used

### Requirement: Report-page module keys are profile-specific

For `side_2d_kinematics_5page_v1`, `section.module_key` SHALL identify the
report-page aggregation module and SHALL NOT be interpreted as an artifact
`module_key` or a legacy `side_technical` section key.

#### Scenario: Page module key differs from artifact module key

- **WHEN** page 2 of the five-page profile is assembled
- **THEN** `section.module_key` SHALL be `body_posture_head_trunk`
- **AND** each asset within the section SHALL retain its artifact `module_key`
- **AND** `section.source_module_keys` SHALL list the fact source modules

### Requirement: Report assembly status is distinct from upstream status

For `side_2d_kinematics_5page_v1`, the top-level report SHALL expose
`assembly_status` (`ready` / `partial`), separate from the upstream
`artifact_set.status` and `finding_set.status` namespaces.

#### Scenario: Legacy path is unchanged

- **WHEN** the legacy `build_swim_report_data()` path is used
- **THEN** its existing behavior and `status` semantics SHALL remain unchanged
- **AND** the new `assembly_status` field applies only to the five-page profile

## MODIFIED Requirements

### Requirement: Report sections include availability status

`ReportData.sections[]` SHALL include `availability`
(ready/degraded/blocked), `data_confidence` (high/medium/low/null) and
`quality_notes` (string array) fields, representing data availability rather than
technical diagnostic status.

This requirement applies to the legacy `side_technical` profile and its
`build_swim_report_data()` path. The new `side_2d_kinematics_5page_v1` profile
uses `section.status` (ready/partial/unavailable) and `assembly_status` instead,
as defined in the `five-page-kinematics-report` capability. The two profiles
remain independent.

#### Scenario: Blocked section with no findings

- **WHEN** `catch_pull` module availability = `blocked`
- **THEN** the section MUST contain `availability: "blocked"`, `metrics: []`,
  `findings: []`, `quality_notes` explaining the block reason

#### Scenario: Degraded section reports limited data

- **WHEN** `catch_pull` module availability = `degraded` and diagnostics have findings
- **THEN** `status` (technical diagnostic) MAY still be `has_issues`,
  `availability` stays `degraded`, `quality_notes` explains missing data
