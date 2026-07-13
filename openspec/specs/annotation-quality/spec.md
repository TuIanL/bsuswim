# annotation-quality Specification

## Purpose
定义标注质量验证能力，包括 annotation quality validator（标注输入质量）、metric quality evaluator（指标计算质量）和 analysis quality aggregator（两阶段聚合）。覆盖结构化问题码、模块 readiness、profile 系统和重新验证机制。

## Requirements

### Requirement: Quality status uses valid/warning/invalid three-state
系统 SHALL 使用 `valid/warning/invalid` 作为 `NormalizedAnnotation.quality.status` 的枚举值，废弃旧有的 `good/warning/error`。

#### Scenario: Complete annotation returns valid
- **WHEN** annotation 包含 fps、所有核心关键点、关键事件和标尺，且帧范围有效、坐标不越界
- **THEN** `quality.status` MUST 为 `valid`

#### Scenario: Missing scale returns warning
- **WHEN** annotation 缺少标尺（scale 为空或 pixels_per_meter 为 null）但其他检查通过
- **THEN** `quality.status` MUST 为 `warning`

#### Scenario: Missing core keypoints returns invalid
- **WHEN** annotation 缺少肩/肘/腕/髋/膝/踝中任一核心关键点
- **THEN** `quality.status` MUST 为 `invalid`

### Requirement: Quality report has structured schema v2
`AnnotationQualityReport` SHALL 包含 `schema_version`、`status`、`score`、`source_revision`、`validator_version`、`profile`、`validated_at`、`summary`（blocking_count/warning_count）、`issues[]`、`module_readiness{}`。

#### Scenario: Quality report includes all mandatory fields
- **WHEN** 系统生成 AnnotationQualityReport
- **THEN** 输出 MUST 包含 schema_version、status、source_revision、validator_version、profile、validated_at、summary 和 issues

#### Scenario: issues array is empty when no problems
- **WHEN** 所有检查通过且无 warning
- **THEN** `issues` MUST 为空数组

### Requirement: Issues have stable code and structured fields
每个 `QualityIssue` SHALL 包含 `code`（稳定机器码）、`category`、`severity`（error/warning/info）、`blocking`（boolean）、`module`、`path`、`frame`（nullable）、`message`、`user_message`、`suggested_action`。

#### Scenario: Issue references specific frame
- **WHEN** 帧号超出视频范围
- **THEN** issue MUST 包含 `frame` 字段指向越界帧号，`user_message` 为面向教练的中文说明

#### Scenario: Non-blocking issue
- **WHEN** 缺少非核心 event（如 catch_start 而非 hand_entry）
- **THEN** `blocking` MUST 为 `false`

### Requirement: Module readiness has three states
`ModuleReadiness` SHALL 使用 `ready/degraded/blocked` 三态表示每个报告模块的数据可用性。

#### Scenario: All conditions met returns ready
- **WHEN** 模块所需事件、关键点和有效帧数均满足 profile 要求
- **THEN** 该模块的 readiness 状态 MUST 为 `ready`

#### Scenario: Partial conditions returns degraded
- **WHEN** 模块所需部分条件满足但存在警告（如 catch_start 事件仅有一个样本）
- **THEN** 该模块的 readiness 状态 MUST 为 `degraded`

#### Scenario: Missing required data returns blocked
- **WHEN** 模块所需关键点完全缺失
- **THEN** 该模块的 readiness 状态 MUST 为 `blocked`

### Requirement: Annotation quality validator runs independent checks
`AnnotationQualityValidator` SHALL 运行时序有效性（帧范围、事件顺序）、几何有效性（坐标有限值、画面越界）、覆盖率与连续性（关键点覆盖率、事件覆盖率）、模块 readiness 四类检查，不重复 Pydantic/ORM 已覆盖的字段类型校验。

#### Scenario: Frame out of range detected
- **WHEN** `events[].frame` 或 `keypoint_frames[].frame` 超出 `[0, frame_count)` 范围
- **THEN** validator MUST 创建对应 blocking issue

#### Scenario: Coordinate NaN detected
- **WHEN** `KeypointPoint.x` 或 `KeypointPoint.y` 为 NaN 或 Infinity
- **THEN** validator MUST 创建对应 blocking issue

#### Scenario: Coordinate out of bounds detected
- **WHEN** 坐标超出视频画面范围（`x < 0` 或 `x >= video_width` 等）
- **THEN** validator MUST 根据超出程度创建 warning 或 error issue

### Requirement: Profile defines module requirements
`QualityProfile` SHALL 声明每个报告模块所需的事件、关键点和最低覆盖阈值。

#### Scenario: Profile declares body_position requirements
- **WHEN** 使用 `side_technical_v1` profile
- **THEN** `body_position` 模块 MUST 要求 `required_landmarks: [shoulder, hip, ankle]`、`minimum_landmark_coverage: 0.80`、`minimum_sample_frames: 3`

#### Scenario: Profile declares efficiency requirements
- **WHEN** 使用 `side_technical_v1` profile
- **THEN** `efficiency` 模块 MUST 要求 `required_references: [scale]` 和 `required_metrics: [stroke_rate_avg, stroke_length_avg]`

### Requirement: Metric quality evaluator assesses computation reliability
`MetricQualityEvaluator` SHALL 输出 `MetricQualityReport`，包含每个指标的计算状态（available/low_confidence/unavailable）、有效样本数量和跳过原因。

#### Scenario: Metric with sufficient samples
- **WHEN** `elbow_angle_deg_avg` 有 15 个有效帧参与计算
- **THEN** metric_availability MUST 为 `available`

#### Scenario: Metric with very few samples
- **WHEN** `elbow_angle_deg_avg` 仅 1 个有效帧
- **THEN** metric_availability MUST 为 `low_confidence`，issues 包含 `ELBOW_ANGLE_SAMPLE_LOW`

### Requirement: Aggregator combines annotation and metric quality
`AnalysisQualityAggregator` SHALL 接收 `AnnotationQualityReport` 和 `MetricQualityReport`，输出 `AnalysisQualitySummary`（含 `annotation`、`metrics`、`decision` 命名空间）。

#### Scenario: Both annotation and metrics valid
- **WHEN** annotation quality = `valid` 且 metrics quality 所有指标均为 `available`
- **THEN** `decision.analysis_allowed` MUST 为 `true`，`decision.report_availability` MUST 为 `full`

#### Scenario: Valid annotation with low-confidence metrics
- **WHEN** annotation quality = `valid` 但部分指标为 `low_confidence`
- **THEN** `decision.report_availability` MUST 为 `degraded`，对应模块 `module_availability` 为 `degraded`

#### Scenario: Invalid annotation
- **WHEN** annotation quality = `invalid`
- **THEN** `decision.analysis_allowed` MUST 为 `false`，`decision.report_availability` MUST 为 `blocked`

### Requirement: Module availability combines both layers
`combine_availability()` SHALL 按 "annotation quality 可阻断、metrics quality 只可降级不可提升" 规则合并模块状态。

#### Scenario: Annotation blocked prevails over metric good
- **WHEN** annotation quality = `blocked` 且 metric quality 计算成功
- **THEN** 组合后的模块状态 MUST 为 `blocked`

#### Scenario: Annotation degraded with metric warning keeps degraded
- **WHEN** annotation quality = `degraded` 且 metric quality = `warning`
- **THEN** 组合后的模块状态 MUST 为 `degraded`

### Requirement: Validate endpoint supports re-validation
`POST /api/normalized-annotations/{id}/validate` SHALL 根据 `(source_revision + validator_version + profile_version)` 判断缓存是否有效，支持 `force=true` 跳过缓存。

#### Scenario: Fresh revision triggers re-validation
- **WHEN** annotation 的 `revision` 大于缓存的 `source_revision`
- **THEN** 系统 MUST 执行完整验证并更新 quality

#### Scenario: Force re-validation ignores cache
- **WHEN** 调用方传递 `force=true`
- **THEN** 系统 MUST 执行完整验证，即使缓存有效

### Requirement: Issue code namespace is stable
Issue code SHALL 按领域前缀分类：`VIDEO_`（上下文）、`FRAME_`（时序）、`KEYPOINT_`（几何）、`EVENT_`（覆盖率）、`ANNOTATION_`（门禁）。

#### Scenario: Temporal issue has FRAME_ prefix
- **WHEN** 帧号超出范围
- **THEN** issue code MUST 以 `FRAME_` 开头，如 `FRAME_OUT_OF_RANGE`

#### Scenario: Coverage issue has EVENT_ prefix
- **WHEN** 缺少必需事件
- **THEN** issue code MUST 以 `EVENT_` 开头，如 `EVENT_HAND_ENTRY_MISSING`

### Requirement: Legacy quality is backward-compatible
`normalize_quality_payload()` SHALL 将旧 schema（`level: good/warning/error`、`checks[]`、`usable_modules[]`、`disabled_modules[]`）映射为新 schema 所需字段。

#### Scenario: Legacy good maps to valid
- **WHEN** 旧 `quality.level = "good"`
- **THEN** 适配后 `quality.status` MUST 为 `valid`

#### Scenario: Legacy error maps to invalid
- **WHEN** 旧 `quality.level = "error"`
- **THEN** 适配后 `quality.status` MUST 为 `invalid`

### Requirement: CVAT source without events is warning not invalid
当 `source = "cvat"` 且 `events` 为空时，quality checker SHALL 标记为 warning 而非 invalid，按指标级可用性聚合模块 readiness。

#### Scenario: CVAT source with empty events yields warning
- **WHEN** `source = "cvat"`，keypoint_frames 完整且有效，但 events 为空
- **THEN** `quality.status` MUST 为 `warning`

### Requirement: Indicator-level availability over module-level
quality profile SHALL 按具体指标声明依赖，指标 availability 聚合为模块 readiness。不按大模块笼统声明 availability。

#### Scenario: CVAT source keypoints only, metric level
- **WHEN** `source = "cvat"`，只有 keypoint_frames，无 events 无 scale，有 timestamp_sec
- **THEN** 肘角膝角指标 MUST 为 `ready`，wrist_speed_px_per_s MUST 为 `ready`，wrist_speed_m_per_s MUST 为 `blocked`（缺 scale），stroke_rate MUST 为 `blocked`（缺 cycle 边界事件）

#### Scenario: Module aggregated from indicators
- **WHEN** `body_position` 模块的所有核心指标（身体轴角度）为 `ready`
- **THEN** `body_position` readiness MUST 为 `ready`

#### Scenario: Module partially degraded
- **WHEN** `efficiency` 模块中 speed_px_per_s 为 `ready` 但 speed_m_per_s 为 `blocked`
- **THEN** `efficiency` readiness MUST 为 `degraded`，包含可用子集清单

### Requirement: Indicator availability matrix for source=cvat
以下为 `source=cvat` 场景下的指标级可用性矩阵：

| 指标 | 必需条件 |
|------|---------|
| elbow_angle_deg, knee_angle_deg | 对应关键点 visible |
| body_axis_angle | 肩、髋关键点 |
| hip_depth_px | 髋点 |
| hip_depth_cm | 髋点 + waterline + scale |
| wrist_trajectory_shape | 连续 wrist 关键点 |
| wrist_speed_px_per_s | 关键点 + timestamp_sec |
| wrist_speed_m_per_s | 关键点 + timestamp_sec + scale |
| stroke_cycle_duration | cycle 边界事件 + timestamp_sec |
| stroke_rate | cycle 边界事件 + timestamp_sec |
| stroke_length | cycle 边界 + scale |
| swolf | distance + time + stroke_count |

#### Scenario: Scale absent blocks physical speed and distance
- **WHEN** `scale` 缺失
- **THEN** `wrist_speed_m_per_s`、`hip_depth_cm`、`stroke_length`、`swolf` MUST 为 `blocked`；`elbow_angle_deg`、`wrist_speed_px_per_s` MUST 仍为 `ready`

#### Scenario: Events absent blocks cycle-based metrics
- **WHEN** `events` 为空
- **THEN** `stroke_cycle_duration`、`stroke_rate`、`stroke_length`、`swolf` MUST 为 `blocked`

### Requirement: Unverified time mapping blocks time metrics
当 `frame_mapping.verified = false` 或 `mode = "unknown"` 时，依赖 `timestamp_sec` 的指标 SHALL 标记为 blocked。

#### Scenario: v2 unverified blocks time metrics
- **WHEN** `schema_version = "swim-annotation.v2"` 且 `frame_mapping.verified = false`
- **THEN** `wrist_speed_px_per_s`、`wrist_speed_m_per_s`、`stroke_cycle_duration`、`stroke_rate` MUST 为 `blocked`，`elbow_angle_deg` MUST 仍为 `ready`，quality warnings 包含 `TIME_MAPPING_UNVERIFIED`

#### Scenario: Verified time mapping enables timing metrics
- **WHEN** `frame_mapping.verified = true` 且其他条件满足
- **THEN** 时间类指标 readiness MUST 根据各自必需条件正常评估

### Requirement: v1 compatibility for time metrics
`swim-annotation.v1` 时间类指标继续使用 `frame / fps` 兼容计算，不受 v2 `verified` 规则影响。

#### Scenario: v1 time metrics computed via frame/fps
- **WHEN** `schema_version = "swim-annotation.v1"`
- **THEN** 时间类指标 SHALL 使用 `frame / fps` 推导时间戳，不受 `frame_mapping.verified` 影响

### Requirement: Unannotated frames do not trigger missing point errors
`annotation_sequence.frame_count` 与 `annotated_frame_count` 的差值 SHALL 视为"未标注帧"，而非"标注缺失帧"，不触发错误级别的 quality issue。

#### Scenario: 56 annotated out of 356 total is warning
- **WHEN** `annotated_frame_count = 56`，`annotation_sequence.frame_count = 356`
- **THEN** quality MUST 为 `warning` 而非 `invalid`，issue 为 `SEQUENCE_COVERAGE_LOW`（info 级别）

#### Scenario: Analysis range fully covered
- **WHEN** `analysis_ranges` 声明范围为 0–55，`annotated_frame_count = 56`
- **THEN** 覆盖率 MUST 视为 100%，不生成 `SEQUENCE_COVERAGE_LOW` issue

### Requirement: Kinovea source unchanged
`source = "kinovea"` 的 quality 评估规则 SHALL 不受 CVAT 新增规则影响。

#### Scenario: Kinovea rules unchanged
- **WHEN** `source = "kinovea"`
- **THEN** quality checker MUST 使用现有规则，不应用 CVAT 来源的 availability 矩阵
