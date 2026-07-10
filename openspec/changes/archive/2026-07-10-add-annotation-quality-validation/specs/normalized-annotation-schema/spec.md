# normalized-annotation-schema Specification (Delta)

## MODIFIED Requirements

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

### Requirement: Scale is nullable with quality gating
系统 SHALL 允许 `scale` 为空。当 `scale` 为空或缺少 `pixels_per_meter` 时，validator MUST 将 `quality.status` 标记为 `warning` 并将 distance 相关模块标记为 `blocked`。

#### Scenario: Missing scale blocks distance modules
- **WHEN** 创建 normalized annotation 且未提供 `scale`
- **THEN** 系统 MUST 允许创建成功，但 `efficiency` 模块 availability MUST 为 `blocked`

### Requirement: Parse endpoint returns quality status and readiness
`POST /api/annotations/{annotation_file_id}/parse` 响应 SHALL 在 `quality` 中包含 `status`（valid/warning/invalid），并新增 `analysis_readiness`（can_submit / requires_acknowledgement / blocking_issue_count / affected_modules）。

#### Scenario: Parse returns quality and readiness
- **WHEN** parse 成功
- **THEN** `ParseResponse.quality.status` MUST 为 valid/warning/invalid，`ParseResponse.analysis_readiness` MUST 包含 can_submit、requires_acknowledgement、blocking_issue_count

#### Scenario: Parse succeeds with invalid quality
- **WHEN** parse 成功但 quality = invalid
- **THEN** 响应 MUST 返回 `201`，`annotation_file.status` = `parsed`，`quality.status` = `"invalid"`，`analysis_readiness.can_submit` = `false`
