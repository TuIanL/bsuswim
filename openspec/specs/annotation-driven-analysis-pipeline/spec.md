# Capability: annotation-driven-analysis-pipeline

## Purpose

基于持久化标注（NormalizedAnnotation）驱动的分析流水线能力：根据 pipeline_type / pipeline_version 路由执行，顺序产出指标、视觉资产、待复核发现、分析结果及五页报告，并定义任务重试、版本校验、报告持久化与状态聚合等统一协议。

## Requirements

### Requirement: Analysis tasks are routed by pipeline type

系统 SHALL 根据持久化的 pipeline_type 和 pipeline_version 选择分析执行路径。

#### Scenario: Annotation task is submitted

- **WHEN** 用户提交 normalized_annotation_id
- **AND** 未显式指定其他 pipeline
- **THEN** 系统 SHALL 创建 pipeline_type=annotation_kinematics 的任务
- **AND** pipeline_version SHALL 为 side_2d_v1
- **AND** 系统 MUST NOT 调用 ModelServiceClient

#### Scenario: Model task is submitted without annotation input

- **WHEN** 用户未提供 normalized_annotation_id
- **AND** 未显式指定 pipeline_type
- **THEN** 系统 SHALL 保持 model_service 执行路径

#### Scenario: Hybrid pipeline is requested

- **WHEN** pipeline_type=hybrid
- **THEN** 系统 SHALL 返回 PIPELINE_NOT_IMPLEMENTED
- **AND** MUST NOT 静默回退到其他 pipeline

### Requirement: Annotation input is revision locked

系统 SHALL 使用任务提交时锁定的 annotation ID 和 revision。

#### Scenario: Annotation remains unchanged

- **WHEN** 任务执行时 annotation.revision 与任务快照一致
- **THEN** 系统 SHALL 使用该 annotation 执行指标计算

#### Scenario: Annotation revision changes

- **WHEN** annotation.revision 与任务快照不一致
- **THEN** 系统 SHALL 将任务标记为 failed
- **AND** error_code SHALL 为 ANNOTATION_REVISION_DRIFT
- **AND** 系统 MUST NOT 使用新 revision 静默继续

### Requirement: Annotation pipeline executes all required products

系统 SHALL 顺序执行指标、视觉资产、待复核发现、分析结果和五页报告。

#### Scenario: Full pipeline succeeds

- **WHEN** annotation_kinematics task 开始执行
- **THEN** 系统 SHALL 持久化当前 AnnotationMetric
- **AND** SHALL 生成或复用当前 KinematicArtifactSet
- **AND** SHALL 生成或复用当前 KinematicReviewFindingSet
- **AND** SHALL 创建或更新 AnalysisResult
- **AND** SHALL 装配五页 swim-report.v1
- **AND** SHALL 创建或更新 ReportMetadata
- **AND** SHALL 将任务标记为 completed

### Requirement: Pipeline stages are observable

系统 SHALL 持久化具体执行阶段和进度。

#### Scenario: Task is processing

- **WHEN** pipeline 进入一个新步骤
- **THEN** task.stage SHALL 更新为对应阶段
- **AND** progress SHALL 单调递增
- **AND** execution_state SHALL 记录步骤状态与产物引用

### Requirement: Pipeline products are idempotent

系统 SHALL 在相同输入和版本下复用已经完成的产物。

#### Scenario: Failed task is retried

- **WHEN** 用户重试失败的 annotation_kinematics task
- **AND** annotation revision 未变化
- **THEN** 系统 SHALL 复用当前有效的 AnnotationMetric
- **AND** SHALL 复用当前 ready/partial artifact set
- **AND** SHALL 复用当前 ready finding set
- **AND** MUST NOT 产生重复的逻辑产物

### Requirement: Failed tasks can be retried

系统 SHALL 允许任务所有者重试失败任务。

#### Scenario: Owner retries failed task

- **WHEN** task.status=failed
- **AND** 当前用户拥有该 task 的 session
- **THEN** 系统 SHALL 将任务重新置为 queued
- **AND** SHALL 使用原始 input snapshot
- **AND** SHALL 增加 attempt_count

#### Scenario: Non-failed task is retried

- **WHEN** task.status 不是 failed
- **THEN** 系统 SHALL 拒绝 retry 请求

### Requirement: Review findings retain conservative semantics

系统 SHALL 保持 review findings 与 diagnostics 的语义边界。

#### Scenario: AnalysisResult is created

- **WHEN** annotation pipeline 创建 AnalysisResult
- **THEN** KinematicReviewFindingSet MUST NOT 被转换为确定性 diagnostics
- **AND** AnalysisResult.raw_result SHALL 保存 finding set 引用
- **AND** 五页报告 SHALL 以 review_required 形式展示 findings

### Requirement: Five-page report is persisted as the current session report

系统 SHALL 将装配结果写入当前 session 的 ReportMetadata。

#### Scenario: Session already has a report

- **WHEN** annotation pipeline 完成报告装配
- **AND** session 已有 ReportMetadata
- **THEN** 系统 SHALL 整体替换 report_data
- **AND** source SHALL 为 annotation_kinematics
- **AND** task_id SHALL 更新为当前任务
- **AND** 已导出的 PDF SHALL 标记为 stale

### Requirement: The current session report follows last-successful-write semantics

系统 SHALL 采用“最后一次成功持久化报告者胜出”的当前报告投影语义。

#### Scenario: Different pipelines complete for the same session

- **GIVEN** a session already has a report produced by one pipeline
- **WHEN** another pipeline successfully assembles and persists a report
- **THEN** the new report SHALL replace the current `ReportMetadata.report_data`
- **AND** `task_id` and `source` SHALL identify the winning pipeline
- **AND** fields from the previous report SHALL NOT be merged into the new payload

#### Scenario: A later pipeline fails before report persistence

- **GIVEN** a session already has a valid current report
- **WHEN** another pipeline fails before successfully persisting its report
- **THEN** the existing report SHALL remain unchanged

### Requirement: Background pipeline resolves its owner from the task snapshot

系统 SHALL 在后台执行时从任务快照解析执行用户，而非请求上下文。

#### Scenario: Owner resolves successfully

- **WHEN** annotation pipeline 进入 validating_input
- **AND** task.session.coach_id 对应一个存在的 User
- **THEN** 系统 SHALL 将该 User 传给 review-findings 与 report-assembly 服务

#### Scenario: Owner cannot be resolved

- **WHEN** task.session.coach_id 不对应任何 User
- **THEN** 系统 SHALL 将任务标记为 failed
- **AND** error_code SHALL 为 TASK_OWNER_UNAVAILABLE
- **AND** 系统 MUST NOT 伪造只含 id 的 User 对象

### Requirement: All pipelines expose a unified async protocol

系统 SHALL 通过统一 async `run(task_id, pipeline_version)` 协议分派 pipeline，
dispatcher MUST NOT 按具体 pipeline 类型做特殊判断。

#### Scenario: Dispatcher invokes any pipeline uniformly

- **WHEN** 执行器需要运行某个 task
- **THEN** 系统 SHALL 通过 `await registry.resolve(task.pipeline_type).run(task.id, task.pipeline_version)` 调度
- **AND** annotation_kinematics 的同步阻塞工作 SHALL 在线程池内部完成

### Requirement: Report content is stable per generation signature

报告内容 SHALL 只依赖稳定的来源输入，不得包含随重试变化的执行信息。

#### Scenario: Retry produces identical report content

- **WHEN** 同一输入重试且 generation_signature 不变
- **THEN** report_data SHALL 不变
- **AND** 稳定的来源信息 SHALL 写入 `source_trace`
- **AND** task_id / analysis_result_id / attempt SHALL NOT 写入 report_data

### Requirement: Session analysis status is derived by an aggregator

TrainingSession.status SHALL 由 `refresh_session_analysis_status` 聚合推导，
annotation pipeline MUST NOT 无条件直接写 session 状态。

#### Scenario: Mixed pipeline outcomes

- **GIVEN** 同一 session 存在 annotation 已完成任务与 model_service 失败任务
- **WHEN** 状态聚合运行
- **THEN** TrainingSession.status SHALL 为 completed（存在 completed 任务或有效报告）
- **AND** 系统 MUST NOT 因失败任务将其改写为 failed

#### Scenario: All tasks failed

- **GIVEN** session 所有分析任务均 failed 且无有效报告
- **WHEN** 状态聚合运行
- **THEN** TrainingSession.status SHALL 为 failed

### Requirement: Report persistence is serialized per session

报告持久化 SHALL 在 session 行锁保护下进行，防止同 session 多 task 并发覆盖。

#### Scenario: Concurrent pipelines for same session

- **GIVEN** 两个不同 task 同属一个 session 同时到达报告持久化
- **THEN** 系统 SHALL 通过 session 行锁串行化写入
- **AND** 最终仅保留最后成功提交的报告为 current report

### Requirement: Pipeline failure rolls back before recording

失败处理 SHALL 先回滚工作 session，再用独立 session 记录失败状态。

#### Scenario: Database error during a step

- **WHEN** 某步骤抛出数据库异常使工作 session 进入 failed transaction
- **THEN** 系统 SHALL 先 rollback
- **AND** SHALL 用独立 SessionLocal 记录 failed_stage / error_code
- **AND** 任务 SHALL 进入稳定 failed 状态而非卡在 processing

### Requirement: Retry is scoped to annotation_kinematics

本 Change 的 retry API SHALL 仅支持 annotation_kinematics 任务。

#### Scenario: Retry an annotation task

- **WHEN** task.status=failed 且 pipeline_type=annotation_kinematics
- **THEN** 系统 SHALL 允许 retry

#### Scenario: Retry a model_service task

- **WHEN** task.pipeline_type=model_service
- **THEN** 系统 SHALL 拒绝 retry（保留既有 actions）

### Requirement: Pipeline version default and mismatch rejection

系统 SHALL 在提交时解析 pipeline_version 默认值并拒绝不匹配组合。

#### Scenario: Empty version is defaulted

- **WHEN** pipeline_type=annotation_kinematics 且 pipeline_version 为空
- **THEN** 系统 SHALL 默认 side_2d_v1

#### Scenario: Mismatched type and version

- **WHEN** pipeline_type=model_service 且 pipeline_version=side_2d_v1
- **THEN** 系统 SHALL 在提交时拒绝，error_code SHALL 为 UNSUPPORTED_PIPELINE_VERSION

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
