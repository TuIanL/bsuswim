# normalized-annotation-schema Specification

## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: Parse route returns typed ParseResponse
Parse endpoint SHALL 返回 `ParseResponse` 实例，由 service 层提供 `ParseAnnotationResult`（含 annotation、summary、warnings），route 层装配为 `ParseResponse`。

#### Scenario: Service returns ParseAnnotationResult
- **WHEN** `parse_annotation_file` 成功解析
- **THEN** service MUST 返回包含 `annotation`、`summary` 和 `warnings` 的结果对象

#### Scenario: Quality checker scope remains structural
- **WHEN** quality checker 评估 parse 产物
- **THEN** 系统 MUST 继续保持 source-agnostic 结构检查（fps、events、keypoint_frames、scale），不新增游泳专项语义检查
