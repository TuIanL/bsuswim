## MODIFIED Requirements

### Requirement: Pages two through four are category based

Pages 2, 3 and 4 SHALL group content by analysis module category: page 2 covers
`body_posture` and `head_trunk`, page 3 covers `upper_limb`, page 4 covers
`lower_limb`, each drawing metrics, assets and findings from its category.
Within each category, ready `annotated_keyframe` assets SHALL be presented as
diagnostic evidence before or alongside chart assets, retaining artifact identity,
frame references, metric values and source annotation revision. A keyframe SHALL
NOT be interpreted as an action-phase label.

#### Scenario: Body and head-trunk data are available

- **THEN** page 2 SHALL contain `body_posture` and `head_trunk`
  metrics, assets and findings
- **AND** ready keyframe assets SHALL be grouped under their originating module
- **AND** each displayed keyframe SHALL retain its annotation frame and source revision when available

#### Scenario: Upper-limb data are available

- **THEN** page 3 SHALL contain `upper_limb` metrics, assets and findings
- **AND** ready upper-limb keyframes SHALL be displayed with their metric meaning and frame references

#### Scenario: Lower-limb data are available

- **THEN** page 4 SHALL contain `lower_limb` metrics, assets and findings
- **AND** ready lower-limb keyframes SHALL be displayed with their metric meaning and frame references

#### Scenario: A category has no ready keyframe

- **WHEN** a category has no ready annotated keyframe asset
- **THEN** its page SHALL remain renderable
- **AND** the page SHALL show a structured quality note when keyframes were skipped or unavailable
- **AND** chart and metric content SHALL not be removed solely because keyframes are unavailable

### Requirement: The system assembles a fixed five-page kinematics report

The system SHALL assemble a `swim-report.v1` document using report profile
`side_2d_kinematics_5page_v1`.

The document SHALL contain exactly five sections with `page_number` values
`[1, 2, 3, 4, 5]`, including when pages 2 through 4 contain diagnostic keyframe evidence.

#### Scenario: Keyframe evidence is available

- **GIVEN** a current metric, artifact set and finding set are available
- **WHEN** the report is assembled
- **THEN** the report SHALL contain exactly five sections
- **AND** its page numbers SHALL remain `[1, 2, 3, 4, 5]`
- **AND** keyframe evidence SHALL be included inside the category pages rather than an additional page
