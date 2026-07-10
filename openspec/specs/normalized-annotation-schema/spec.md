# normalized-annotation-schema Specification

## Purpose
定义标准化标注数据模型 `normalized_annotations`，作为 annotation_files 和 analysis_results 之间的稳定观测输入层。统一 events、keypoint_frames、trajectories、manual_tags、scale、coordinate_system、quality 子结构，使后续 metrics engine 和 diagnostics engine 不依赖 Kinovea 等具体标注工具。
## Requirements
### Requirement: Normalized annotation uses session_video_id as canonical reference
系统 SHALL 以 `session_video_id` 作为 `normalized_annotations` 的唯一归属引用，关联到 `session_videos` 表。`camera_view` 从 `session_videos.view_type` 推导，不在 `normalized_annotations` 中冗余存储。

#### Scenario: Create normalized annotation with session_video_id
- **WHEN** 系统创建一条 normalized annotation 记录
- **THEN** 系统 MUST 通过 `session_video_id` 外键关联到 `session_videos.id`，且不存储独立的 `session_id`、`video_file_id`、`camera_view` 字段

#### Scenario: Query normalized annotation includes camera_view from session_video
- **WHEN** 调用方查询 normalized annotation 详情
- **THEN** 系统 MUST 通过 `session_videos.view_type` 返回机位信息

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

### Requirement: Source enum reuses AnnotationSource
系统 SHALL 复用 Change #1 定义的 `AnnotationSource` 枚举（kinovea / dartfish / manual_json / ai_pose / unknown）作为 `normalized_annotations.source` 字段的约束值。

#### Scenario: Valid source values accepted
- **WHEN** 创建或更新 normalized annotation 时提供 `source` 值
- **THEN** 系统 MUST 仅接受 `kinovea`、`dartfish`、`manual_json`、`ai_pose`、`unknown` 作为有效值

### Requirement: Scale is nullable with quality gating
系统 SHALL 允许 `scale` 为空。当 `scale` 为空或缺少 `pixels_per_meter` 时，quality checker MUST 将 `quality.level` 标记为 `error` 或 `warning` 并禁用距离相关模块。

#### Scenario: Normalized annotation without scale
- **WHEN** 创建 normalized annotation 且未提供 `scale`
- **THEN** 系统 MUST 允许创建成功，但 quality checker MUST 标记该记录无法计算速度、划幅、距离等空间指标

#### Scenario: Normalized annotation with complete scale
- **WHEN** 创建 normalized annotation 且提供了包含 `pixels_per_meter` 的 `scale`
- **THEN** quality checker MUST 将 scale 检查项标记为 `passed`

### Requirement: Quality checker validates minimum data requirements
系统 SHALL 实现 quality checker，至少检查 `has_fps`、`has_events`、`has_keypoint_frames`、`has_core_keypoints`、`has_scale`、`event_frame_range_valid`、`keypoint_frame_range_valid` 七项。

#### Scenario: All checks passed yields good quality
- **WHEN** fps、events、keypoint_frames（含肩/肘/腕/髋/膝/踝）、scale 均完整且 frame 范围有效
- **THEN** quality checker MUST 返回 `level = "good"`

#### Scenario: Missing scale yields warning quality
- **WHEN** fps、events、keypoint_frames 完整但缺少 scale
- **THEN** quality checker MUST 返回 `level = "warning"`，`usable_modules` 排除距离相关模块

#### Scenario: Missing keypoint_frames yields error quality
- **WHEN** 缺少 keypoint_frames 或 events
- **THEN** quality checker MUST 返回 `level = "error"`

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

### Requirement: swimm-annotation.v1 schema version constant
系统 SHALL 将 `schema_version` 默认值设为 `swim-annotation.v1`，所有新创建的 normalized annotation MUST 携带此版本标识。

#### Scenario: New normalized annotation has swim-annotation.v1 schema
- **WHEN** 系统创建一条新的 normalized annotation 记录
- **THEN** `schema_version` MUST 为 `swim-annotation.v1`

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

