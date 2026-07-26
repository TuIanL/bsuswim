## MODIFIED Requirements

### Requirement: Issues have stable code and structured fields
每个 `QualityIssue` SHALL 包含 `code`（稳定机器码）、`category`、`severity`（error/warning/info）、`blocking`（boolean）、`module`、`path`、`frame`（nullable）、`message`、`user_message`、`suggested_action`。对于可由质量修复工作台处理的问题，`suggested_action` SHALL 包含稳定的 action type、用户可见 label 和打开修复步骤所需的 payload。

#### Scenario: Issue references specific frame
- **WHEN** 帧号超出视频范围
- **THEN** issue MUST 包含 `frame` 字段指向越界帧号，`user_message` 为面向教练的中文说明

#### Scenario: Non-blocking issue
- **WHEN** 缺少非核心 event（如 catch_start 而非 hand_entry）
- **THEN** `blocking` MUST 为 `false`

#### Scenario: Repairable issue includes action
- **WHEN** issue code is `SCALE_INVALID`、`SCALE_MISSING`、`WATERLINE_MISSING`、`SWIM_DIRECTION_UNSET`、`COMPLETE_CYCLE_INSUFFICIENT` 或 `TIME_MAPPING_UNVERIFIED`
- **THEN** issue MUST include `suggested_action.type` and `suggested_action.label`
- **AND** action type MUST map to a supported repair workbench step

### Requirement: Validate endpoint supports re-validation
`POST /api/normalized-annotations/{id}/validate` SHALL 根据 `(source_revision + validator_version + profile_version)` 判断缓存是否有效，支持 `force=true` 跳过缓存；质量修复保存后 SHALL 递增 `source_revision` 并使旧缓存失效。

#### Scenario: Fresh revision triggers re-validation
- **WHEN** annotation 的 `revision` 大于缓存的 `source_revision`
- **THEN** 系统 MUST 执行完整验证并更新 quality

#### Scenario: Force re-validation ignores cache
- **WHEN** 调用方传递 `force=true`
- **THEN** 系统 MUST 执行完整验证，即使缓存有效

#### Scenario: Repair revision invalidates cache
- **WHEN** quality repair successfully increments annotation revision
- **THEN** the next validation MUST NOT return the prior revision's cached quality
- **AND** `quality.source_revision` MUST equal the new annotation revision

