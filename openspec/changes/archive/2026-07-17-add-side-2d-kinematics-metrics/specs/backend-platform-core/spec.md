## ADDED Requirements

### Requirement: Calculator registry

The system SHALL provide a calculator registry mapping calculator names to their implementations.

#### Scenario: Registry contains both calculators
- **WHEN** the registry is initialized
- **THEN** it SHALL contain at least `side_view_metrics` and `side_2d_kinematics`

### Requirement: source_revision column

The system SHALL track annotation revision in the annotation_metrics table.

#### Scenario: Metric is persisted
- **WHEN** a metric result is saved
- **THEN** `source_revision` SHALL be set to the normalized annotation's revision

#### Scenario: Stale detection
- **WHEN** `source_revision` differs from the current annotation revision
- **THEN** `revision_status` SHALL be `"stale"`

#### Scenario: Legacy record compatibility
- **WHEN** `source_revision` is NULL
- **THEN** `revision_status` SHALL be `"unknown"`
- **AND** `is_stale` SHALL be false
