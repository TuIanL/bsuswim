# reference-revision-resolution Specification

## Purpose
TBD - created by archiving change add-manual-temporal-reference-labeling-workspace. Update Purpose after archive.
## Requirements
### Requirement: 显式 resolver 按 set 与 revision 解析

系统 SHALL 提供统一 resolver，显式按 `annotation_set_id` + `revision_id` 解析人工参考标注。resolver MUST 拒绝任何"按 session 取最新"的隐式行为。

#### Scenario: 按 set 与 revision 成功解析

- **WHEN** 调用 `resolve_reference_labels(set_id, revision_id)` 且两者匹配且存在
- **THEN** resolver MUST 返回该 revision 下全部未删除 segment 及完整 provenance

#### Scenario: set 与 revision 不匹配时报错

- **WHEN** 传入的 `revision_id` 不属于传入的 `annotation_set_id`
- **THEN** resolver MUST 返回 `revision_mismatch`，MUST NOT 回退到该 set 的其他 revision

#### Scenario: resolver 不提供 latest 便捷路径

- **WHEN** 检查 resolver 的接口定义
- **THEN** resolver MUST NOT 提供仅按 `session_video_id` 返回最新标注的入口

#### Scenario: revision 不存在时返回 not_found

- **WHEN** 传入不存在的 `revision_id`
- **THEN** resolver MUST 返回 `not_found`，MUST NOT 回退到 imported events 而不产生提示

### Requirement: resolver 校验视频 checksum

系统 SHALL 在解析时比对 revision 记录的 `video_checksum_sha256` 与当前 session video 所关联 `VideoFile.checksum_sha256`，不匹配时报告冲突。

#### Scenario: checksum 一致时正常返回

- **WHEN** revision 记录的 checksum 与当前视频一致
- **THEN** resolver MUST 返回 `ready` 状态

#### Scenario: checksum 不一致时报告冲突

- **WHEN** revision 记录的 checksum 与当前视频不一致
- **THEN** resolver MUST 返回 `checksum_mismatch`，并 MUST NOT 静默返回标注数据

#### Scenario: 视频不存在时降级

- **WHEN** session video 未关联 `VideoFile`
- **THEN** resolver MUST 返回 `checksum_unknown` 并在 warning 中说明，MUST NOT 阻止解析

### Requirement: AnalysisTask 使用独立外键快照 reference revision

系统 SHALL 在 `analysis_tasks` 增加 `reference_annotation_revision_id` 列，外键指向 `manual_annotation_revisions.id`，可空。

#### Scenario: 创建任务时快照 revision

- **WHEN** 用户创建分析任务并指定人工参考标注
- **THEN** 系统 MUST 将 `reference_annotation_revision_id` 写入该任务的 FK 列

#### Scenario: 外键为空时行为不变

- **WHEN** 分析任务未指定人工参考标注
- **THEN** `reference_annotation_revision_id` MUST 为 NULL，分析行为 MUST 与本次改动前一致

#### Scenario: 后续标注修改不影响已快照任务

- **WHEN** 某任务已快照 revision A，之后用户 fork 出 revision B 并继续修改
- **THEN** 该任务 MUST 仍引用 revision A，MUST NOT 因 B 的产生而改变

#### Scenario: revision 被删除时外键置空

- **WHEN** 被引用的 revision 被硬删除
- **THEN** `reference_annotation_revision_id` MUST 被置为 NULL，任务记录 MUST 保留

### Requirement: request_payload 镜像 provenance

系统 SHALL 在 `AnalysisTask.request_payload.analysis_input` 中镜像参考标注的 provenance 信息。

#### Scenario: 镜像包含完整 provenance

- **WHEN** 分析任务快照了某 revision
- **THEN** `request_payload.analysis_input` MUST 包含 `reference_annotation_set_id`、`reference_annotation_revision_id`、`revision_no`、`content_hash`、`video_checksum_sha256`、`phase_profile_id`、`phase_profile_version`

#### Scenario: 镜像与外键一致

- **WHEN** 检查同一任务的 FK 列与 `request_payload` 镜像
- **THEN** 两者的 `reference_annotation_revision_id` MUST 一致

#### Scenario: 历史任务无镜像字段时可读

- **WHEN** 读取本次改动前创建的历史任务
- **THEN** 系统 MUST 正常读取，MUST NOT 因 `request_payload` 缺少参考标注字段而报错

### Requirement: 下游消费显式 revision，不得重新查询 latest

metrics、diagnostics 与 report 装配 MUST 消费任务快照的 `reference_annotation_revision_id`，MUST NOT 重新按 session 查询最新标注。

#### Scenario: metrics 使用快照 revision

- **WHEN** 系统为某任务计算指标
- **THEN** 输入标注 MUST 来自 `reference_annotation_revision_id` 解析结果，MUST NOT 来自按 session 查询的最新标注

#### Scenario: 快照缺失时显式回退并告警

- **WHEN** 任务未指定 reference revision 但存在 imported events
- **THEN** 系统 MUST 回退到 imported events，并 MUST 在 quality 或 warning 中显式记录该回退

#### Scenario: profile 不匹配时返回 profile_mismatch

- **WHEN** 任务快照的 `phase_profile_hash` 与 revision 记录的不一致
- **THEN** resolver MUST 返回 `profile_mismatch`，MUST NOT 返回标注数据

#### Scenario: 快照 revision 不可用时阻断而非回退

- **WHEN** 任务指定了 reference revision 但 resolver 返回 `not_found`、`revision_mismatch`、`checksum_mismatch` 或 `profile_mismatch`
- **THEN** 系统 MUST 返回 `reference_input_invalid` 并阻断相关分析，MUST NOT 改用其他 revision，MUST NOT 回退到 imported events

#### Scenario: 未指定时才允许回退

- **WHEN** 任务未指定 reference revision
- **THEN** 系统 MUST 允许回退到 imported events，并 MUST 显式记录该回退

