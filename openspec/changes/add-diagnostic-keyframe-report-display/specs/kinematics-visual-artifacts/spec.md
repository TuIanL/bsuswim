## MODIFIED Requirements

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
- presentation metadata for ready annotated keyframes, including a human-readable title, selection meaning, display metric label/unit and caption

#### Scenario: A keyframe manifest is consumed by the report

- **WHEN** a ready `annotated_keyframe` is projected into `swim-report.v1`
- **THEN** its presentation metadata SHALL be available to the report asset
- **AND** the report SHALL retain the original artifact key for traceability

### Requirement: Keyframe overlays remain factual

Annotated frames SHALL display COCO17 skeletons, objective geometry and metric values only. Embedded titles and captions SHALL use a renderable Chinese font or a reliable fallback and SHALL NOT contain replacement glyphs for the supported Chinese display text.

#### Scenario: Body-axis overlay is generated

- **WHEN** body_axis_angle_deg is displayed
- **THEN** the reference SHALL be labelled screen horizontal
- **AND** the image MUST NOT label the angle as a water-surface angle
- **AND** the title SHALL identify the metric and extremum without claiming an action phase

#### Scenario: Chinese text cannot use the preferred font

- **WHEN** the preferred renderer font is unavailable
- **THEN** the renderer SHALL select a configured fallback font
- **AND** SHALL produce readable title and caption text rather than question-mark replacement glyphs
