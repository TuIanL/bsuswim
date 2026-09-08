## ADDED Requirements

### Requirement: 分析流水线消费显式快照的 reference revision

分析流水线 SHALL 消费任务快照中 `reference_annotation_revision_id` 所指向的人工参考标注，MUST NOT 按 session 重新查询最新人工标注。

本需求与既有的 `Annotation input is revision locked` 并存：前者锁定 `normalized_annotations.revision`（导入标注），本需求锁定 `manual_annotation_revisions.id`（人工参考标注）。

#### Scenario: 任务指定了 reference revision

- **WHEN** 任务的 `reference_annotation_revision_id` 非空且 resolver 返回 `ready`
- **THEN** 流水线 MUST 使用该 revision 的 segments 作为权威输入，MUST NOT 重新按 session 查询

#### Scenario: 任务未指定 reference revision

- **WHEN** 任务的 `reference_annotation_revision_id` 为 NULL
- **THEN** 流水线 MUST 回退到 imported events，行为 MUST 与本次改动前一致

#### Scenario: 回退必须显式记录

- **WHEN** 流水线因缺少 reference revision 而回退到 imported events
- **THEN** 系统 MUST 在 quality 或 warning 中记录该回退，MUST NOT 静默执行

#### Scenario: reference revision 不可用时阻断

- **WHEN** resolver 返回 `not_found`、`revision_mismatch` 或 `checksum_mismatch`
- **THEN** 流水线 MUST 生成 warning，MUST NOT 静默改用其他 revision

### Requirement: 双重 revision 锁定

分析流水线 SHALL 同时锁定导入标注的 `normalized_annotations.revision` 与人工参考标注的 `manual_annotation_revisions.id`，任一漂移 MUST 被检出。

#### Scenario: 人工标注后续修改不影响运行中任务

- **WHEN** 任务已快照 reference revision A，随后用户 fork 出 revision B 并修改
- **THEN** 该任务 MUST 继续使用 A，MUST NOT 因 B 的产生而漂移

#### Scenario: 两类 revision 同时快照

- **WHEN** 任务同时引用导入标注与人工参考标注
- **THEN** 任务 MUST 分别记录两者的 revision 标识，MUST NOT 用单一 revision 字段混表达两者

### Requirement: 分析输入来源可追溯

流水线 SHALL 在产物中记录本次分析实际使用的标注来源（`manual_segments` 或 `imported_events`）及其标识。

#### Scenario: 记录实际使用的标注来源

- **WHEN** 流水线完成指标计算
- **THEN** 产物 MUST 记录 `source_of_truth` 取值及对应 revision 标识

#### Scenario: 来源为人工时记录 profile 版本

- **WHEN** 本次分析使用人工参考标注
- **THEN** 产物 MUST 记录 `phase_profile_id` 与 `phase_profile_version`
