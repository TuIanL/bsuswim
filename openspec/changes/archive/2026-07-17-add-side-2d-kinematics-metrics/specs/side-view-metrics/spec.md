## MODIFIED Requirements

### Requirement: calculate-metrics endpoint accepts calculator parameter

The system SHALL accept a `calculator` query parameter on `POST /normalized-annotations/{id}/calculate-metrics`.

#### Scenario: Default calculator is side_view_metrics
- **WHEN** no calculator parameter is provided
- **THEN** the system SHALL use `side_view_metrics` as the default calculator

#### Scenario: Explicit calculator selection
- **WHEN** `calculator=side_2d_kinematics`
- **THEN** the system SHALL invoke the side_2d_kinematics calculator

### Requirement: Metrics query filters by calculator

The system SHALL filter annotation metric reads by calculator name. The existing GET endpoint SHALL be extended with calculator and calculator_version parameters.

#### Scenario: Request specific calculator metrics
- **WHEN** `GET /normalized-annotations/{id}/metrics?calculator=side_2d_kinematics`
- **THEN** the system SHALL return only metrics where calculator = "side_2d_kinematics"

#### Scenario: Default calculator is side_view_metrics
- **WHEN** no calculator parameter is provided on GET
- **THEN** the system SHALL default to `side_view_metrics`

#### Scenario: Unknown calculator returns error
- **WHEN** an unsupported calculator name is provided
- **THEN** the system SHALL return 422 with code `unsupported_metric_calculator`
