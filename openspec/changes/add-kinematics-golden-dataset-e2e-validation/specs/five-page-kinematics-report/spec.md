# five-page-kinematics-report (delta)

## MODIFIED Requirements

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

#### Scenario: Video metadata provenance uses SessionVideo, not VideoFile

- **WHEN** `side_2d_kinematics_5page_v1` 报告构建 video context
- **THEN** FPS SHALL 取自 `SessionVideo.fps`
- **AND** resolution SHALL 取自 `SessionVideo.resolution`
- **AND** VideoFile 仅用于文件身份（`id` 与 `original_filename`）
- **AND** 无权威持久化时长时 `duration_sec` SHALL 为 null
- **AND** 报告构建器 MUST NOT 读取未声明的 `VideoFile.fps` / `VideoFile.width` / `VideoFile.height` / `VideoFile.duration_sec`
- **AND** `report.context.video.fps` SHALL 等于绑定 SessionVideo 的 FPS
- **AND** `report.context.video.resolution` SHALL 等于 SessionVideo 的 resolution

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

#### Scenario: Artifact quality notes are scoped to the page source modules

- **WHEN** an artifact is skipped or degraded and produces a quality note
- **THEN** the note SHALL carry `module_key`, `artifact_key` and `metric_keys`
- **AND** the note SHALL be shown only on pages whose `source_module_keys` contain that `module_key`
- **AND** an upper-limb artifact degradation SHALL appear on page 3 `upper_limb_kinematics`
- **AND** page 2 `body_posture_control` and page 4 `lower_limb_kinematics` MUST NOT show an upper-limb specific degradation note
- **AND** page 5 `review_and_retest` MAY aggregate the degradation but is not the primary assertion target
