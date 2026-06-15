# swim-interactive-performance-report Specification

## Purpose
TBD - created by archiving change port-pickleball-platform-to-swim-analysis. Update Purpose after archive.
## Requirements
### Requirement: Swim performance report
The system SHALL provide interactive swim analysis reports based on demo or job-specific report data.

#### Scenario: User opens a swim report
- **WHEN** the user opens a report view
- **THEN** the system displays session context, summary metrics, key findings, and report-source clarity for the selected swim analysis job or demo dataset

#### Scenario: Report data is limited
- **WHEN** a report module lacks algorithm-derived data
- **THEN** the system labels the module as demo, unavailable, or limited rather than presenting unsupported metrics as real analysis

### Requirement: Swim posture diagnostics
The report SHALL surface coach-readable posture and technique diagnostics.

#### Scenario: User reviews diagnostic findings
- **WHEN** diagnostic findings are available
- **THEN** the system displays issue title, severity, evidence, coach suggestion, expected improvement, and priority for swim-specific topics such as body line, breathing timing, hand entry, catch, kick rhythm, or hip rotation

### Requirement: Stroke rhythm and symmetry metrics
The report SHALL include swim-specific metrics that can support training comparison.

#### Scenario: User reviews metric cards
- **WHEN** report metrics are visible
- **THEN** the system shows metrics such as stroke rhythm, body angle stability, left-right symmetry, kick consistency, breathing timing, and overall technique score

#### Scenario: User reviews trend or progress information
- **WHEN** trend data is available
- **THEN** the system presents the change in readable units and does not imply precision beyond the available demo or algorithm source

### Requirement: Training feedback loop
The system SHALL translate swim analysis findings into training recommendations.

#### Scenario: User opens training feedback
- **WHEN** the user opens the training view
- **THEN** the system displays recommended drills, linked technique issues, practice tasks, target outcomes, and progress toward the next training goal

#### Scenario: User follows a recommendation from a report
- **WHEN** the user selects a training recommendation from a report or workspace
- **THEN** the system opens the training feedback context associated with that analysis or demo recommendation

### Requirement: Report visual consistency
Report and training views SHALL retain the dark 智泳云枢 platform design language.

#### Scenario: User compares report views with homepage
- **WHEN** the user moves from the homepage into reports or training feedback
- **THEN** typography, color, panel treatment, icon usage, spacing, and interaction states feel like one product rather than an imported bright dashboard

