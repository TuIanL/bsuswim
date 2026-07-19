## MODIFIED Requirements

### Requirement: Pipeline progress is exposed as a typed shared contract
任务读取接口 SHALL 通过统一的 `PipelineProgressRead` 暴露流水线类型、版本、执行步骤、失败步骤、错误码与 actions，且 `AnalysisTaskRead` 与 `AnalysisStatusRead` SHALL 由同一 serializer 构造。

#### Scenario: Status route returns real pipeline metadata
- **WHEN** 前端调用 `GET /analysis/{task_id}/status`
- **THEN** 响应 MUST 包含真实 `pipeline_type`、`pipeline_version`、`attempt_count`、`failed_stage`、`error_code`
- **AND** MUST 包含 `pipeline_progress`（有序 steps 数组，每步含 status=pending|running|completed|failed、progress、details）
- **AND** MUST 包含派生的 `actions`

#### Scenario: Missing steps projected as pending
- **WHEN** 任务 `execution_state.steps` 尚未写入全部七阶段
- **THEN** `pipeline_progress.steps` MUST 以规范顺序返回全部七阶段
- **AND** 未出现的步骤 MUST 投影为 `pending`
- **AND** `task.stage` 对应步骤 MUST 为 `running`
- **AND** `task.failed_stage` 对应步骤 MUST 为 `failed`

### Requirement: Failed tasks distinguish retry from resubmit by error type
失败任务 SHALL 根据错误类型区分 `retry` 与 `resubmit` 动作。

#### Scenario: Processing error exposes retry
- **WHEN** 失败错误码属于执行阶段类（METRIC_PERSIST_FAILED / ARTIFACT_GENERATION_FAILED / REVIEW_FINDINGS_GENERATION_FAILED / REPORT_ASSEMBLY_FAILED / PIPELINE_INTERNAL_ERROR）
- **THEN** `actions` MUST 包含 `retry`
- **AND** 前端 MUST 调用 `POST /analysis/{task_id}/retry`

#### Scenario: Input or revision error exposes resubmit
- **WHEN** 失败错误码属于输入/版本类（INVALID_INPUT / ANNOTATION_NOT_FOUND / ANNOTATION_REVISION_DRIFT / SESSION_MISMATCH / UNSUPPORTED_VIEW / NO_KEYPOINT_FRAMES）
- **THEN** `actions` MUST 包含 `resubmit`
- **AND** 前端 MUST 通过 `POST /analysis/submit` 以当前标注创建新任务

### Requirement: Submit prevents duplicate active annotation tasks
`create_analysis_task()` SHALL 在创建 annotation_kinematics 任务前原子地检查同一 session 下是否已有活跃任务。

#### Scenario: Active annotation task conflict
- **WHEN** 同一 session 已存在 `pipeline_type=annotation_kinematics` 且 status 为 queued/processing/result_saving 的任务
- **THEN** 系统 MUST 返回 HTTP 409 `ANALYSIS_TASK_ALREADY_ACTIVE`
- **AND** 响应 MUST 包含 `existing_task_id`
- **AND** MUST NOT 影响既有 model_service 任务
