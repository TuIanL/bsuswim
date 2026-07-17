# normalized-annotation-schema Specification

## Purpose
定义标准化标注数据模型 `normalized_annotations`，作为 annotation_files 和 analysis_results 之间的稳定观测输入层。统一 events、keypoint_frames、trajectories、manual_tags、scale、coordinate_system、quality 子结构，使后续 metrics engine 和 diagnostics engine 不依赖 Kinovea 等具体标注工具。
## Requirements
### Requirement: Normalized annotation uses session_video_id as canonical reference
系统 SHALL 以 `session_video_id` 作为 `normalized_annotations` 的唯一归属引用。Video metadata 从 `session_video.video_file` 获取，存入 `annotation_metadata.video`。

#### Scenario: Create normalized annotation with session_video_id
- **WHEN** 系统创建一条 normalized annotation 记录
- **THEN** 系统 MUST 通过 `session_video_id` 外键关联到 `session_videos.id`，且不存储独立的 `session_id`、`video_file_id`、`camera_view` 字段

#### Scenario: Video metadata sourced from session_video
- **WHEN** CVAT parser 创建 NormalizedAnnotation
- **THEN** 系统 MUST 通过 `session_video.video_file` 获取 video 元数据并存入 `annotation_metadata.video`

### Requirement: Annotation file reference is nullable
系统 SHALL 允许 `annotation_file_id` 为空，支持从不依赖原始文件的来源（manual JSON、AI pose 直出）创建标准化标注。

#### Scenario: Create from manual JSON without annotation file
- **WHEN** 调用方通过 JSON API 创建 normalized annotation 且不提供 `annotation_file_id`
- **THEN** 系统 MUST 创建记录并将 `annotation_file_id` 设为 NULL

#### Scenario: Create from annotation file parse
- **WHEN** 系统解析一个 `annotation_file_id` 并生成 normalized annotation
- **THEN** 系统 MUST 将 `annotation_file_id` 外键指向源文件

### Requirement: Upsert on re-parse with revision increment
系统 SHALL 对同一 `annotation_file_id` 重复 parse 时 upsert 现有 normalized annotation 记录并递增 `revision`。

#### Scenario: First parse creates record with revision 1
- **WHEN** 系统首次解析某个 `annotation_file_id`
- **THEN** 系统 MUST 创建 normalized annotation 记录，`revision = 1`

#### Scenario: Second parse updates record with revision 2
- **WHEN** 系统再次解析同一个 `annotation_file_id`
- **THEN** 系统 MUST 更新同一条 normalized annotation 记录，`revision` 递增为 2

#### Scenario: Multiple manual JSON records for same session_video
- **WHEN** 调用方对同一 `session_video_id` 多次使用 JSON API 创建 normalized annotation（`annotation_file_id = NULL`）
- **THEN** 系统 MUST 允许创建多条记录

### Requirement: Parse endpoint derives session_video_id from annotation file
`POST /api/annotations/{annotation_file_id}/parse` 端点 SHALL 从 `annotation_files.session_video_id` 推导归属关系，不接受客户端提供的 `session_video_id`。

#### Scenario: Parse uses annotation file's session_video_id
- **WHEN** 调用方请求 `POST /api/annotations/{annotation_file_id}/parse`
- **THEN** 系统 MUST 通过 `annotation_files.session_video_id` 确定归属，创建或更新 normalized annotation

#### Scenario: Parse rejects client-provided session_video_id
- **WHEN** 调用方在 parse 请求中提供 `session_video_id`
- **THEN** 系统 MUST 忽略或拒绝该参数，仅使用 `annotation_file` 的归属

### Requirement: Source enum includes cvat
系统 SHALL 扩展 `AnnotationSource` 枚举，增加 `cvat` 为有效来源值。PostgreSQL 数据库中的 `annotationsource` 枚举类型 SHALL 同时通过 ALTER TYPE 语句增加 `cvat` 值，确保 ORM 写入不报错。

#### Scenario: Valid source values include cvat
- **WHEN** 创建或更新 normalized annotation 时提供 `source = "cvat"`
- **THEN** 系统 MUST 接受 `cvat` 作为有效值
- **THEN** PostgreSQL 层 MUST 不因 ENUM 值不存在而报 `invalid input value for enum` 错误

#### Scenario: PostgreSQL enum updated by migration

- **WHEN** 开发者执行新增 migration
- **THEN** `ALTER TYPE annotationsource ADD VALUE IF NOT EXISTS 'cvat'` MUST 成功执行
- **THEN** `SELECT unnest(enum_range(NULL::annotationsource))` 结果 MUST 包含 `cvat`

#### Scenario: Downgrade is no-op

- **WHEN** 开发者执行 `alembic downgrade -1`
- **THEN** migration 的 downgrade MUST 不报错（PostgreSQL 不支持安全移除 enum value）

#### Scenario: Existing sources unchanged
- **WHEN** 枚举已包含 `kinovea`、`dartfish`、`manual_json`、`ai_pose`、`unknown`
- **THEN** 新增 `cvat` 后 MUST 不影响已有枚举值

### Requirement: Scale is nullable with quality gating
系统 SHALL 允许 `scale` 为空。当 `scale` 为空或缺少 `pixels_per_meter` 时，validator MUST 将 `quality.status` 标记为 `warning` 并将 distance 相关模块标记为 `blocked`。

#### Scenario: Missing scale blocks distance modules
- **WHEN** 创建 normalized annotation 且未提供 `scale`
- **THEN** 系统 MUST 允许创建成功，但 `efficiency` 模块 availability MUST 为 `blocked`

### Requirement: Quality checker validates minimum data requirements
系统 SHALL 通过 `AnnotationQualityValidator` 校验标注质量，至少覆盖时序有效性、几何有效性、覆盖率和模块 readiness 四类。

#### Scenario: All checks passed yields valid quality
- **WHEN** fps、events、keypoint_frames（含肩/肘/腕/髋/膝/踝）、scale 均完整且 frame 范围有效、坐标不越界
- **THEN** `AnnotationQualityValidator` MUST 返回 `status = "valid"`

#### Scenario: Missing scale yields warning quality
- **WHEN** fps、events、keypoint_frames 完整但缺少 scale
- **THEN** `quality.status` MUST 为 `warning`

#### Scenario: Missing keypoint_frames yields invalid quality
- **WHEN** 缺少 keypoint_frames 或 events
- **THEN** `quality.status` MUST 为 `invalid`

### Requirement: Event-level labeling uses labeled_by field
标准化标注中事件级标注来源 SHALL 使用 `labeled_by` 字段（manual / kinovea / ai / derived），与顶层 `source` 区分。

#### Scenario: Event with manual labeling
- **WHEN** 教练手动标记入水事件
- **THEN** 该事件的 `labeled_by` MUST 为 `manual`

#### Scenario: Event derived from AI
- **WHEN** AI 姿态识别输出事件
- **THEN** 该事件的 `labeled_by` MUST 为 `ai`

### Requirement: Coordinate system stored independently
系统 SHALL 将 `coordinate_system` 作为独立 JSONB 列存储，包含 `origin`、`x_axis`、`y_axis`、`unit` 字段。

#### Scenario: Pixel coordinate system
- **WHEN** 标注数据使用视频像素坐标
- **THEN** `coordinate_system` MUST 记录 `unit = "pixel"` 和 `origin = "top_left"`

#### Scenario: Normalized coordinate system
- **WHEN** 标注数据使用 AI 模型归一化坐标
- **THEN** `coordinate_system` MUST 记录 `unit = "normalized"` 和对应的原点定义

### Requirement: Create normalized annotation from JSON
系统 SHALL 提供 `POST /api/session-videos/{session_video_id}/normalized-annotations` 端点，接受 JSON body 创建标准化标注记录。

#### Scenario: Create minimal valid normalized annotation
- **WHEN** 调用方提交包含 fps、events、keypoint_frames 的 JSON body
- **THEN** 系统 MUST 创建 normalized annotation 记录，运行 quality checker，返回 id 和 quality

#### Scenario: Create with optional annotation_file_id
- **WHEN** 调用方在 JSON body 中提供 `annotation_file_id`
- **THEN** 系统 MUST 将记录关联到该 annotation file

### Requirement: Get normalized annotation by ID
系统 SHALL 提供 `GET /api/normalized-annotations/{normalized_annotation_id}` 端点，返回完整标准化标注对象。

#### Scenario: Retrieve existing normalized annotation
- **WHEN** 调用方请求有效的 `normalized_annotation_id`
- **THEN** 系统 MUST 返回完整 JSON，包含 video 信息、events、keypoint_frames、trajectories、manual_tags、scale、coordinate_system、quality

#### Scenario: Retrieve non-existent normalized annotation
- **WHEN** 调用方请求不存在的 `normalized_annotation_id`
- **THEN** 系统 MUST 返回 404

### Requirement: List normalized annotations by session video
系统 SHALL 提供 `GET /api/session-videos/{session_video_id}/normalized-annotations` 端点，返回指定视频绑定下的所有标准化标注列表。

#### Scenario: List returns all versions for a session video
- **WHEN** 调用方请求某个 `session_video_id` 的标准化标注列表
- **THEN** 系统 MUST 返回该视频下所有 normalized annotation 的摘要列表（id、source、schema_version、quality_level、revision、created_at）

### Requirement: Parse status linkage with annotation_files
parse 端点成功生成 normalized annotation 后 SHALL 更新 `annotation_files.status = 'parsed'`；解析失败 SHALL 更新 `annotation_files.status = 'parse_failed'` 并写入 `parse_error`。

#### Scenario: Parse success updates annotation file status
- **WHEN** `POST /api/annotations/{annotation_file_id}/parse` 成功生成 normalized annotation
- **THEN** 系统 MUST 将对应 `annotation_files` 记录的 status 更新为 `parsed`

#### Scenario: Parse failure updates annotation file status
- **WHEN** parse 过程失败
- **THEN** 系统 MUST 将对应 `annotation_files` 记录的 status 更新为 `parse_failed`，并将错误信息写入 `parse_error`

### Requirement: SQLAlchemy model uses annotation_metadata attribute
系统 SHALL 在 SQLAlchemy 模型中以 `annotation_metadata` 作为 Python 属性名，映射到数据库列 `metadata`（JSONB），避免与 SQLAlchemy Base.metadata 冲突。

#### Scenario: Access annotation_metadata from ORM
- **WHEN** 代码通过 ORM 访问标准化标注的元数据
- **THEN** 系统 MUST 通过 `normalized_annotation.annotation_metadata` 获取扩展信息
### Requirement: schema_version stays at swim-annotation.v1

新创建的 NormalizedAnnotation SHALL 使用 `swim-annotation.v1` 作为 schema_version。所有来源（包括 CVAT）均使用此版本。

#### Scenario: CVAT source uses swim-annotation.v1
- **WHEN** 系统为 source = "cvat" 解析创建 NormalizedAnnotation
- **THEN** `schema_version` MUST 为 `swim-annotation.v1`

#### Scenario: Manual JSON uses swim-annotation.v1
- **WHEN** 通过 JSON API 手动创建 NormalizedAnnotation（不指定 schema_version）
- **THEN** `schema_version` MUST 默认为 `swim-annotation.v1`

### Requirement: Parse response schema includes summary and warnings
`ParseResponse` SHALL 扩展为包含 `annotation_file_id`、`source`、`summary`（events/keypoint_frames/trajectories/manual_tags 计数）和 `warnings`（语义提醒列表）。Parse route SHALL 使用 `response_model=ParseResponse`。

#### Scenario: Parse response includes summary
- **WHEN** parse 成功
- **THEN** 响应 MUST 包含 `summary.events_count`、`summary.keypoint_frames_count`、`summary.trajectories_count`、`summary.manual_tags_count`

#### Scenario: Parse response includes warnings
- **WHEN** parse 过程中 parser 生成语义 warnings（如缺少推荐事件）
- **THEN** 响应 MUST 在 `warnings` 数组中包含这些提醒

#### Scenario: Parse response includes annotation_file_id and source
- **WHEN** parse 成功
- **THEN** 响应 MUST 包含 `annotation_file_id` 和 `source` 字段

#### Scenario: Parse route uses response_model
- **WHEN** parse endpoint 返回响应
- **THEN** 系统 MUST 通过 `response_model=ParseResponse` 进行序列化和校验，而非手写 dict

### Requirement: Parse route returns typed ParseResponse
Parse endpoint SHALL 返回 `ParseResponse` 实例，由 service 层提供 `ParseAnnotationResult`（含 annotation、summary、warnings），route 层装配为 `ParseResponse`。

#### Scenario: Service returns ParseAnnotationResult
- **WHEN** `parse_annotation_file` 成功解析
- **THEN** service MUST 返回包含 `annotation`、`summary` 和 `warnings` 的结果对象

#### Scenario: Quality checker scope remains structural
- **WHEN** quality checker 评估 parse 产物
- **THEN** 系统 MUST 继续保持 source-agnostic 结构检查（fps、events、keypoint_frames、scale），不新增游泳专项语义检查

### Requirement: reference_lines carries waterline
系统 SHALL 在 `normalized_annotations` 支持 `reference_lines` 字段（JSONB），至少含 `waterline` 子结构 `{points: [[x1,y1],[x2,y2]], confidence, source}`。

#### Scenario: Create with waterline
- **WHEN** 创建 normalized annotation 并在 `reference_lines.waterline` 提供两点
- **THEN** 系统 MUST 存储该水面线，metrics 引擎可据此计算 `hip_depth_cm`

#### Scenario: Absent waterline degrades hip_depth
- **WHEN** annotation 不含 `reference_lines.waterline`
- **THEN** quality checker MUST 允许创建成功，但 metrics 层 MUST 将 `hip_depth_cm` 置为 null 并记 `missing_waterline` warning

### Requirement: distance_markers for speed and stroke length
系统 SHALL 支持 `distance_markers` 字段（JSONB 数组），元素含 `frame`、`time_sec`、`distance_m`、`source`，用于在 clips 内推导瞬时速度、划幅与相位分段。

#### Scenario: Create with distance_markers
- **WHEN** 创建 normalized annotation 并提供 `distance_markers`
- **THEN** 系统 MUST 存储，metrics 层可据其计算 `average_speed_mps`、`stroke_length_m`（优先级1）与 `phase_metrics`

#### Scenario: Absent distance_markers
- **WHEN** annotation 不含 `distance_markers`
- **THEN** `average_speed_mps` / `stroke_length_m`（距离版）/ `phase_metrics` MUST 降级或为空，并记 `no_phase_context` / 相应 warning，不报错

### Requirement: swim_direction for front reach sign
系统 SHALL 支持 `swim_direction` 字段（如 `left_to_right` / `right_to_left`），用于消除 `front_reach_distance_cm` 等方向上的正负歧义。

#### Scenario: Create with swim_direction
- **WHEN** 创建 normalized annotation 并指定 `swim_direction`
- **THEN** 系统 MUST 存储，metrics 层据其确定前伸距离的符号方向

#### Scenario: Absent swim_direction
- **WHEN** annotation 不含 `swim_direction`
- **THEN** 系统 MUST 允许创建；`front_reach_distance_cm` 以绝对值计算，quality 标注方向未消歧（不阻塞）

### Requirement: Schema migration adds three fields
系统 SHALL 通过 alembic 迁移为 `normalized_annotations` 表新增 `reference_lines`、`distance_markers`、`swim_direction` 三列（JSONB / 字符串），不破坏现有数据。

#### Scenario: Migration applies cleanly
- **WHEN** 执行新增迁移
- **THEN** 现有 `normalized_annotations` 记录的这三个字段 MUST 默认为空/Null，旧记录仍可正常读取

### Requirement: Quality checker aware of new fields
quality checker SHALL 在缺 `waterline` 时将 `hip_depth_cm` 相关模块标记为不可用（warning 级），不因新字段缺失而整体 error。

#### Scenario: Waterline missing is warning not error
- **WHEN** fps、scale、关键点、事件均完整但缺 `reference_lines.waterline`
- **THEN** quality.level MUST 为 `warning`，`usable_modules` 排除依赖 waterline 的指标，`hip_depth_cm` 降级


### Requirement: Quality checker scope remains structural
旧 requirement 删去"不新增游泳专项语义检查"的限制，改由 profile 定义 swim 语义要求。

#### Scenario: Profile defines semantic requirements
- **WHEN** `side_technical_v1` profile 要求 hand_entry 事件
- **THEN** validator MUST 检查该语义要求，缺失时标记为 warning（而非 blocking）

### Requirement: reference_lines/distance_markers/swim_direction degrade not block
quality checker SHALL 在缺 `waterline` 时将 `hip_depth_cm` 相关模块标记为 degraded（warning 级），不因新字段缺失而整体 invalid。

#### Scenario: Waterline missing is degraded not invalid
- **WHEN** fps、scale、关键点、事件均完整但缺 `reference_lines.waterline`
- **THEN** `quality.status` MUST 为 `warning`，`hip_depth_cm` 相关模块 availability 为 `degraded`

### Requirement: Parse endpoint returns quality status and readiness
`POST /api/annotations/{annotation_file_id}/parse` 响应 SHALL 在 `quality` 中包含 `status`（valid/warning/invalid），并新增 `analysis_readiness`（can_submit / requires_acknowledgement / blocking_issue_count / affected_modules）。

#### Scenario: Parse returns quality and readiness
- **WHEN** parse 成功
- **THEN** `ParseResponse.quality.status` MUST 为 valid/warning/invalid，`ParseResponse.analysis_readiness` MUST 包含 can_submit、requires_acknowledgement、blocking_issue_count

#### Scenario: Parse succeeds with invalid quality
- **WHEN** parse 成功但 quality = invalid
- **THEN** 响应 MUST 返回 `201`，`annotation_file.status` = `parsed`，`quality.status` = `"invalid"`，`analysis_readiness.can_submit` = `false`

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

### Requirement: Parse warnings persisted in annotation_metadata

`parse_annotation_file()` SHALL 将 warnings 持久化到 `NormalizedAnnotation.annotation_metadata.parse.warnings`。

#### Scenario: Warnings written on successful parse
- **WHEN** parse 成功且产生 warnings
- **THEN** `annotation_metadata.parse.warnings` MUST 包含 warning 列表
- **AND** `annotation_metadata.parse.parsed_at` MUST 为解析时间戳

#### Scenario: Warnings overwritten on re-parse
- **WHEN** 同一文件重新解析
- **THEN** `annotation_metadata.parse.warnings` MUST 被新 warnings 覆盖
- **AND** MUST NOT 追加到旧 warnings

#### Scenario: Parse failure does not overwrite metadata
- **WHEN** parse 失败
- **THEN** 系统 MUST NOT 修改 `annotation_metadata.parse`

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
### Requirement: Unique constraint alignment

SQLAlchemy model 的约束定义 SHALL 与 Alembic migration 中的约束定义一致，避免 `alembic check` 报漂移。

#### Scenario: NormalizedAnnotation no duplicate unique

- **WHEN** `NormalizedAnnotation` ORM 模型定义中 `annotation_file_id` 列同时有 `unique=True` 和 `__table_args__` 中的 `UniqueConstraint`
- **THEN** 系统 MUST 删除列上的 `unique=True`，保留 `__table_args__` 中的命名唯一约束

#### Scenario: AnnotationMetric has model-level unique constraint

- **WHEN** `AnnotationMetric` ORM 模型定义
- **THEN** 系统 MUST 在 `__table_args__` 中声明 `UniqueConstraint("normalized_annotation_id", "calculator", "calculator_version", name="uq_annotation_metrics_calc")`

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
