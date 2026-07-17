## ADDED Requirements

### Requirement: AnnotationFrameRange schema

系统 SHALL 新增 `AnnotationFrameRange` 模型，包含 `start_annotation_frame` 和 `end_annotation_frame` 两个整数字段。

#### Scenario: AnnotationFrameRange structure
- **WHEN** 创建 annotation coverage 的 `annotated_ranges` 或 `analysis_ranges`
- **THEN** 元素 MUST 使用 `start_annotation_frame` 和 `end_annotation_frame` 作为 range 边界字段

### Requirement: Coverage ranges derived from real annotation frames

系统 SHALL 根据 keypoint_frames 的实际 `annotation_frame` 生成 `annotation_coverage.annotated_ranges`，而非使用连续计数推断。

#### Scenario: Contiguous frames form single range
- **WHEN** keypoint_frames 的 annotation_frame 为 `[32, 33, 34, 35]`
- **THEN** `annotated_ranges` MUST 为 `[{start_annotation_frame: 32, end_annotation_frame: 35}]`

#### Scenario: Sparse frames form multiple ranges
- **WHEN** keypoint_frames 的 annotation_frame 为 `[32, 33, 40, 41, 80]`
- **THEN** `annotated_ranges` MUST 为 `[{start_annotation_frame: 32, end_annotation_frame: 33}, {start_annotation_frame: 40, end_annotation_frame: 41}, {start_annotation_frame: 80, end_annotation_frame: 80}]`

#### Scenario: Single frame range
- **WHEN** keypoint_frames 的 annotation_frame 为 `[40]`
- **THEN** `annotated_ranges` MUST 为 `[{start_annotation_frame: 40, end_annotation_frame: 40}]`

### Requirement: Read path compatible with both old and new coverage keys

系统 SHALL 在读取 `annotated_ranges` 和 `analysis_ranges` 时同时支持 `start_annotation_frame` / `end_annotation_frame` 和旧 `start_frame` / `end_frame`。

#### Scenario: Accept both old and new keys on read
- **WHEN** 读取的 range 包含 `start_frame` 而非 `start_annotation_frame`
- **THEN** 系统 MUST 将 `start_frame` 值作为 `start_annotation_frame` 处理

#### Scenario: New keys take priority
- **WHEN** 读取的 range 同时包含 `start_annotation_frame` 和 `start_frame`
- **THEN** 系统 MUST 使用 `start_annotation_frame`

### Requirement: annotated_ranges and analysis_ranges are independent

系统 SHALL 确保 `annotation_coverage.annotated_ranges` 和顶层 `analysis_ranges` 使用相同的字段命名，但语义分开存储。

#### Scenario: Both ranges stored independently
- **WHEN** 用户指定 `analysis_ranges`
- **THEN** `analysis_ranges` MUST 独立存储，与 `annotated_ranges` 互不影响

#### Scenario: No analysis_ranges defaults empty
- **WHEN** 用户未指定 `analysis_ranges`
- **THEN** `analysis_ranges` MUST 为空数组，`annotated_ranges` 仍按真实帧生成

### Requirement: Frame-count semantics strictly separated

NormalizedAnnotation 的 `frame_count` SHALL 仅表示原视频总帧数。CVAT 任务序列帧数存入 `annotation_sequence.frame_count`。有效骨架帧数存入 `annotation_coverage.annotated_frame_count`。

#### Scenario: frame_count from video file
- **WHEN** `video_file.frame_count` 可用
- **THEN** 顶层 `frame_count` MUST 为原视频总帧数

#### Scenario: frame_count null when unavailable
- **WHEN** `video_file.frame_count` 不可用
- **THEN** 顶层 `frame_count` MUST 为 null，不得使用其他帧数回填

#### Scenario: annotation_sequence from CVAT meta
- **WHEN** CVAT XML 包含 `<job><size>`
- **THEN** `annotation_sequence.frame_count` MUST 为该值
- **AND** `annotation_sequence.start_frame` 和 `end_frame` 来自 CVAT meta

#### Scenario: annotated_frame_count from actual frames
- **WHEN** 解析完成
- **THEN** `annotation_coverage.annotated_frame_count` MUST 等于 `len(keypoint_frames)`

### Requirement: contract_version tracks import contract generation

新创建的 CVAT NormalizedAnnotation SHALL 在 `annotation_metadata` 中写入 `contract_version: "cvat-import-contract.v1.1"`，与 `schema_version` 独立。

#### Scenario: contract_version written on CVAT parse
- **WHEN** 系统为 source = "cvat" 解析创建 NormalizedAnnotation
- **THEN** `annotation_metadata.contract_version` MUST 为 `"cvat-import-contract.v1.1"`

### Requirement: KeypointFrame includes source_track_ids

`KeypointFrame` SHALL 增加可选字段 `source_track_ids: list[str] = Field(default_factory=list)`，从 `RawCvatKeypointFrame.source_track_ids` 传递。

#### Scenario: source_track_ids preserved on normalization
- **WHEN** `RawCvatKeypointFrame.source_track_ids` 包含 `["track_0"]`
- **THEN** 对应 `KeypointFrame.source_track_ids` MUST 为 `["track_0"]`

### Requirement: Parser metadata recorded

系统 SHALL 在 `annotation_metadata` 中记录 parser 的名称、版本和源格式。

#### Scenario: Parser metadata written
- **WHEN** CVAT parse 完成
- **THEN** `annotation_metadata.parser.name` MUST 为 `"cvat_xml"`
- **AND** `annotation_metadata.parser.version` MUST 为 `"1.1.0"`
- **AND** `annotation_metadata.parser.source_format` MUST 为 `"cvat_task_xml"`

## MODIFIED Requirements

### Requirement: schema_version stays at swim-annotation.v1

新创建的 NormalizedAnnotation SHALL 使用 `swim-annotation.v1` 作为 schema_version。所有来源（包括 CVAT）均使用此版本。

#### Scenario: CVAT source uses swim-annotation.v1
- **WHEN** 系统为 source = "cvat" 解析创建 NormalizedAnnotation
- **THEN** `schema_version` MUST 为 `swim-annotation.v1`

#### Scenario: Manual JSON uses swim-annotation.v1
- **WHEN** 通过 JSON API 手动创建 NormalizedAnnotation（不指定 schema_version）
- **THEN** `schema_version` MUST 默认为 `swim-annotation.v1`

### Requirement: Coverage ranges inferred from actual annotation frames

系统 SHALL 根据 keypoint_frames 的实际 `annotation_frame` 生成 `annotation_coverage.annotated_ranges`，不得使用连续计数推断。

#### Scenario: Coverage ranges inferred from keypoint frames
- **WHEN** 未显式提供 `analysis_ranges`
- **THEN** 系统 MUST 从 keypoint_frames 的实际 `annotation_frame` 推断 `annotated_ranges`，不得使用连续计数

## REMOVED Requirements

### Requirement: schema_version upgrades to swim-annotation.v2

**Reason**: 当前 ORM 默认值为 `swim-annotation.v1` 且 service 创建时未显式设置版本。本 Change 将规格对齐代码现状，不进行版本升级。Parser 版本信息以独立 metadata 记录。

**Migration**: 现有 `swim-annotation.v2` 要求从规格中移除。所有新创建标注继续使用 `swim-annotation.v1`。
