# normalized-annotation-schema Specification

## ADDED Requirements

### Requirement: KeypointPoint.x and KeypointPoint.y are nullable
`KeypointPoint.x` 和 `KeypointPoint.y` SHALL 允许为 null，以表示关键点存在骨架定义中但当前帧不可观测。

#### Scenario: Missing keypoint stores null coordinates
- **WHEN** CVAT XML 中某关键点 `outside="1"`
- **THEN** KeypointPoint.x MUST 为 null，KeypointPoint.y MUST 为 null，`visibility` MUST 为 `"missing"`

#### Scenario: Visible keypoint stores float coordinates
- **WHEN** CVAT XML 中某关键点 `outside="0"` 且 `occluded="0"`
- **THEN** KeypointPoint.x MUST 为 float 类型，KeypointPoint.y MUST 为 float 类型，`visibility` MUST 为 `"visible"`

### Requirement: KeypointPoint.visibility adds missing, keeps estimated for compat
`KeypointPoint.visibility` SHALL 支持 `"visible" | "occluded" | "missing" | "estimated"`。`"estimated"` 保留为 deprecated 状态，确保 v1 数据可读。

#### Scenario: CVAT outside=1 maps to missing
- **WHEN** `outside="1"`
- **THEN** visibility MUST 为 `"missing"`

#### Scenario: CVAT occluded=1 maps to occluded
- **WHEN** `outside="0"` 且 `occluded="1"`
- **THEN** visibility MUST 为 `"occluded"`

#### Scenario: CVAT outside=0 occluded=0 maps to visible
- **WHEN** `outside="0"` 且 `occluded="0"`
- **THEN** visibility MUST 为 `"visible"`

#### Scenario: v1 estimated data still readable
- **WHEN** 旧 `swim-annotation.v1` 数据中包含 `visibility: "estimated"`
- **THEN** 系统 MUST 正常读取，不因 Literal 限制拒绝

### Requirement: Coordinate-visibility consistency validated
`KeypointPoint` SHALL 通过 Pydantic model_validator 确保坐标与可见性状态一致。

#### Scenario: missing with coordinates rejected
- **WHEN** `visibility = "missing"` 且 `x` 或 `y` 不为 null
- **THEN** 验证 MUST 失败，抛出 ValueError

#### Scenario: visible with null coordinates rejected
- **WHEN** `visibility = "visible"` 且 `x` 为 null 或 `y` 为 null
- **THEN** 验证 MUST 失败，抛出 ValueError

#### Scenario: occluded with null coordinates rejected
- **WHEN** `visibility = "occluded"` 且 `x` 为 null 或 `y` 为 null
- **THEN** 验证 MUST 失败，抛出 ValueError

#### Scenario: missing with null coordinates passes
- **WHEN** `visibility = "missing"` 且 `x` 为 null 且 `y` 为 null
- **THEN** 验证 MUST 通过

### Requirement: KeypointFrame includes per-frame time mapping fields
`KeypointFrame` SHALL 新增 `annotation_frame`、`source_video_frame`、`timestamp_sec`、`image_name` 四个字段，与现有 `frame` 字段共存。

#### Scenario: All four new fields populated on parse
- **WHEN** 经 CVAT 标准化层生成 KeypointFrame
- **THEN** 系统 MUST 填充 `annotation_frame`（CVAT 帧号）、`source_video_frame`（映射后的原视频帧号）、`timestamp_sec`（时间戳）、`image_name`（图片文件名）

#### Scenario: frame field retained for backward compatibility
- **WHEN** CVAT 标准化层生成 KeypointFrame
- **THEN** `frame` 字段 MUST 与 `annotation_frame` 值相同，保持向下兼容

#### Scenario: Fields nullable when mapping unavailable
- **WHEN** frame_mapping.mode 为 `"unknown"`
- **THEN** `source_video_frame`、`timestamp_sec`、`image_name` MUST 允许为 null

### Requirement: Metadata stored in existing annotation_metadata JSONB
v2 时间轴和覆盖范围元数据 SHALL 统一存入现有的 `annotation_metadata` JSONB 列，不新增独立 SQL 列。

#### Scenario: Metadata structure in annotation_metadata
- **WHEN** CVAT parse 完成并创建 NormalizedAnnotation
- **THEN** `annotation_metadata` MUST 包含 `video`、`annotation_sequence`、`frame_mapping`、`annotation_coverage`、`analysis_ranges` 子结构

#### Scenario: No new SQL columns added
- **WHEN** alembic 迁移执行
- **THEN** `normalized_annotations` 表 MUST NOT 新增独立 JSONB 列用于元数据

### Requirement: Top-level video metadata block
NormalizedAnnotation SHALL 在 `annotation_metadata.video` 中记录原始视频信息。

#### Scenario: Video metadata populated from session_video
- **WHEN** NormalizedAnnotation 创建或更新
- **THEN** `video` MUST 包含 `fps`、`frame_count`、`duration_sec`，值来自关联的 session_video.video_file

#### Scenario: Video metadata nullable
- **WHEN** session_video 缺乏视频文件元数据
- **THEN** `video` 字段中对应值可为 null，不阻止创建

### Requirement: Top-level annotation_sequence metadata
NormalizedAnnotation SHALL 在 `annotation_metadata.annotation_sequence` 中记录 CVAT 任务级帧信息。

#### Scenario: Annotation sequence from CVAT meta
- **WHEN** source = "cvat" 且 XML 包含任务帧范围
- **THEN** `annotation_sequence` MUST 包含 `frame_count`、`start_frame`、`end_frame`

### Requirement: Top-level annotation_coverage metadata
NormalizedAnnotation SHALL 在 `annotation_metadata.annotation_coverage` 中记录实际标注帧的统计数据。

#### Scenario: Coverage from parsed keypoint frames
- **WHEN** 解析完成
- **THEN** `annotation_coverage.annotated_frame_count` MUST 为实际有骨架标注的帧数

#### Scenario: Coverage ranges inferred
- **WHEN** 未显式提供 `analysis_ranges`
- **THEN** 系统 MUST 从 keypoint_frames 的连续帧范围内推断 `annotation_coverage.annotated_ranges[]`

### Requirement: Top-level analysis_ranges
NormalizedAnnotation SHALL 支持 `analysis_ranges` 字段，声明计划分析的时间范围。

#### Scenario: Analysis range specified
- **WHEN** 创建 NormalizedAnnotation 时提供 `analysis_ranges`
- **THEN** 系统 MUST 存储该范围，quality checker 基于此计算覆盖率

#### Scenario: No analysis range defaults to annotated ranges
- **WHEN** 未提供 `analysis_ranges`
- **THEN** 系统 MUST 从 keypoint_frames 的起始和结束帧推断分析范围，quality warning 提示 `analysis_scope_inferred`

### Requirement: schema_version upgrades to swim-annotation.v2
系统 SHALL 将 `schema_version` 默认值升级为 `swim-annotation.v2`，新创建的 CVAT 来源 NormalizedAnnotation 使用 v2。

#### Scenario: CVAT source uses swim-annotation.v2
- **WHEN** 系统为 source = "cvat" 解析创建 NormalizedAnnotation
- **THEN** `schema_version` MUST 为 `swim-annotation.v2`

#### Scenario: Manual JSON still uses swim-annotation.v1
- **WHEN** 通过 JSON API 手动创建 NormalizedAnnotation（不指定 schema_version）
- **THEN** `schema_version` MUST 默认为 `swim-annotation.v1`，保持向下兼容

## MODIFIED Requirements

### Requirement: Normalized annotation uses session_video_id as canonical reference
系统 SHALL 以 `session_video_id` 作为 `normalized_annotations` 的唯一归属引用。Video metadata 从 `session_video.video_file` 获取，存入 `annotation_metadata.video`。

#### Scenario: Create normalized annotation with session_video_id
- **WHEN** 系统创建一条 normalized annotation 记录
- **THEN** 系统 MUST 通过 `session_video_id` 外键关联到 `session_videos.id`，且不存储独立的 `session_id`、`video_file_id`、`camera_view` 字段

#### Scenario: Video metadata sourced from session_video
- **WHEN** CVAT parser 创建 NormalizedAnnotation
- **THEN** 系统 MUST 通过 `session_video.video_file` 获取 video 元数据并存入 `annotation_metadata.video`

### Requirement: Source enum includes cvat
系统 SHALL 扩展 `AnnotationSource` 枚举，增加 `cvat` 为有效来源值。

#### Scenario: Valid source values include cvat
- **WHEN** 创建或更新 normalized annotation 时提供 `source = "cvat"`
- **THEN** 系统 MUST 接受 `cvat` 作为有效值

#### Scenario: Existing sources unchanged
- **WHEN** 枚举已包含 `kinovea`、`dartfish`、`manual_json`、`ai_pose`、`unknown`
- **THEN** 新增 `cvat` 后 MUST 不影响已有枚举值
