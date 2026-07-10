# swim-video-analysis-job-flow Specification

## Purpose
TBD - created by archiving change port-pickleball-platform-to-swim-analysis. Update Purpose after archive.
## Requirements
### Requirement: Swim video upload entry
The system SHALL provide a swim-specific multi-camera video upload entry point for an existing training session.

#### Scenario: User opens the new swim analysis page
- **WHEN** the user opens the video upload entry view for a training session
- **THEN** the system displays a swim training video workflow with current session context, multi-camera file selection, camera view metadata, synchronization offset fields, and actions to save draft or submit analysis

#### Scenario: User enters swim metadata
- **WHEN** the user prepares the training session before upload
- **THEN** the form captures swim-specific metadata such as athlete, session title, venue or pool, session date, stroke type, distance, pool length, scene, and notes

### Requirement: Upload form validation
The system SHALL guide users through valid video selection and required swim session context before submitting an analysis job.

#### Scenario: User selects a supported video
- **WHEN** the user selects a local video file for a camera view
- **THEN** the system shows the file name, file size, camera view, upload status, and allows the video to be bound to the current training session

#### Scenario: User submits incomplete analysis input
- **WHEN** required session context is missing or no session video has been successfully bound
- **THEN** the system keeps the submit-analysis action disabled or presents a clear validation message

### Requirement: Local demo job creation
The system SHALL support local demo analysis jobs so the workflow can be demonstrated without a backend service.

#### Scenario: User starts a demo analysis
- **WHEN** the user submits a valid demo analysis request
- **THEN** the system creates a completed or simulated swim analysis job, stores it locally, and routes the user to task management or the job status view

#### Scenario: User returns later in the same browser
- **WHEN** locally stored demo jobs exist
- **THEN** the task management view lists those jobs in reverse updated order

### Requirement: Analysis task management
The system SHALL provide a task management view for swim training sessions and video analysis jobs.

#### Scenario: User opens task management
- **WHEN** the user opens the analysis task view
- **THEN** the system displays session or job rows with status, progress, athlete or session metadata, updated time, and available next actions

#### Scenario: User opens a completed task
- **WHEN** the user selects a completed swim analysis job
- **THEN** the system routes to job-specific visual analysis, report, or details actions for that job

#### Scenario: User opens a session awaiting upload
- **WHEN** the user selects a training session that has not finished video upload
- **THEN** the system routes to the session-specific multi-camera upload page

### Requirement: Swim analysis stage states
The system SHALL communicate swim-specific analysis progress and terminal states.

#### Scenario: User opens a processing job
- **WHEN** a swim analysis job is queued or processing
- **THEN** the system displays stage labels such as upload, synchronization, stitching, frame sampling, pose detection, stroke segmentation, metric extraction, visualization, and report generation

#### Scenario: User opens a failed or unavailable job
- **WHEN** a swim analysis job fails or cannot be loaded
- **THEN** the system shows a stable error state with a user-facing reason and actions to return to task management or start a new analysis

### Requirement: Backend-ready analysis client
The frontend SHALL isolate auth, athlete, training session, video upload, session-video binding, analysis job, workspace, and report operations behind typed client boundaries.

#### Scenario: Implementation uses local demo data
- **WHEN** no backend service is configured
- **THEN** the client returns local demo users, athletes, sessions, videos, jobs, workspaces, and reports without requiring network access

#### Scenario: Future backend integration is added
- **WHEN** backend endpoints become available
- **THEN** the client boundary can be extended to upload videos, create sessions, bind session videos, create jobs, poll status, and fetch reports without rewriting platform view components

### Requirement: Backend analysis job creation
系统 SHALL 通过业务后端创建真实游泳视频分析任务。

#### Scenario: User submits real video analysis
- **WHEN** 用户选择有效视频文件、创建或选择训练记录、并将视频绑定到该训练记录后提交分析
- **THEN** 前端 MUST 通过 API 上传视频、创建训练记录视频绑定并提交 session 级后端分析任务，而不是只创建本地 demo job

#### Scenario: Backend returns created job
- **WHEN** 后端成功创建分析任务
- **THEN** 系统 MUST 返回任务 ID、训练记录 ID、初始状态、训练记录元数据、已绑定视频摘要和后续状态查询入口

### Requirement: Backend task polling
系统 SHALL 支持前端查询真实分析任务状态。

#### Scenario: User opens task management with backend enabled
- **WHEN** 前端配置了业务后端 API
- **THEN** 任务管理视图 MUST 从后端加载 session 级分析任务列表，并展示数据库中的状态、进度、更新时间和可用操作

#### Scenario: User opens processing task
- **WHEN** 用户打开正在处理的任务
- **THEN** 前端 MUST 轮询或刷新 `GET /api/v1/analysis/{task_id}/status`，并展示后端返回的当前阶段和进度

### Requirement: Model-service-backed terminal states
系统 SHALL 根据模型服务和结果保存过程更新任务终态。

#### Scenario: Model result is saved
- **WHEN** 模型服务返回有效 session 级分析结果且业务后端保存成功
- **THEN** 任务状态 MUST 更新为 `completed`，并暴露可进入可视化工作台和 session 报告页的操作

#### Scenario: Model service fails
- **WHEN** 模型服务返回错误、超时或输出无法验证
- **THEN** 任务状态 MUST 更新为 `failed`，并展示后端保存的错误原因

### Requirement: Training session preparation flow
系统 SHALL 在真实后端分析前建立用户会话、运动员档案、训练记录和视频绑定关系。

#### Scenario: User prepares backend analysis
- **WHEN** 用户准备提交真实游泳视频分析
- **THEN** 系统 MUST 能够通过后端 API 完成注册或登录、恢复当前用户、创建或选择运动员、创建训练记录、上传一个或多个视频并绑定训练记录视频

#### Scenario: Session has no bound video
- **WHEN** 用户尝试提交没有绑定视频的训练记录进行分析
- **THEN** 系统 MUST 拒绝创建分析任务并返回可读错误原因

#### Scenario: Session has multiple camera videos
- **WHEN** 用户为同一训练记录上传多个机位视频
- **THEN** 系统 MUST 为每个视频保存机位类型和 `sync_offset_ms`，并在上传页展示各机位状态

### Requirement: Backend-connected analysis submission
真实后端模式下，Vue 前端 SHALL 在训练记录已绑定至少一个视频后提交 session 级分析任务，而不是创建本地任务或调用旧 task API。

#### Scenario: User submits analysis after binding videos
- **WHEN** 用户在配置了 `VITE_API_BASE_URL` 的 Vue 上传页完成至少一个机位视频上传和训练记录绑定后点击提交分析
- **THEN** 前端 MUST 调用 `POST /api/v1/analysis/submit` 并提交当前 `session_id`

#### Scenario: Backend returns submitted task
- **WHEN** 后端成功创建分析任务并返回 `task_id`、`session_id`、状态、阶段和进度
- **THEN** 前端 MUST 保存返回的任务上下文并导航到该任务的状态、工作台或任务管理入口

#### Scenario: Submission fails
- **WHEN** 后端拒绝分析提交、用户未登录、训练记录不存在或训练记录没有绑定视频
- **THEN** 前端 MUST 展示后端返回的可读错误原因，并保留用户在上传页继续修正

### Requirement: Backend task status polling in Vue
Vue 前端 SHALL 对真实后端分析任务进行状态轮询，并根据终态启用工作台和报告操作。

#### Scenario: Processing task is polled
- **WHEN** 用户打开真实后端任务详情、工作台入口或任务管理视图中的处理中任务
- **THEN** 前端 MUST 轮询 `GET /api/v1/analysis/{task_id}/status` 并展示状态、阶段、进度和错误信息

#### Scenario: Task completes
- **WHEN** 轮询结果显示任务状态为 `completed`
- **THEN** 前端 MUST 停止轮询，并启用进入 `/workspace/{task_id}` 和该任务所属训练记录报告页的操作

#### Scenario: Task fails
- **WHEN** 轮询结果显示任务状态为 `failed`
- **THEN** 前端 MUST 停止轮询，展示后端保存的失败原因，并提供返回任务管理或重新上传分析的操作

### Requirement: Real backend mode avoids legacy local task flow
真实后端模式下，Vue 前端 SHALL 避免使用旧 localStorage 或旧 `/tasks` API 完成分析任务主流程。

#### Scenario: Backend API base URL is configured
- **WHEN** `VITE_API_BASE_URL` 存在且用户执行上传到报告的真实任务流程
- **THEN** 前端 MUST 使用 `/api/v1/videos`、`/api/v1/sessions`、`/api/v1/analysis` 和 `/api/v1/reports` 契约，而不是依赖 localStorage 中的 demo task

#### Scenario: Backend API base URL is absent
- **WHEN** `VITE_API_BASE_URL` 不存在
- **THEN** 前端 MAY 继续使用本地 demo 数据展示上传、任务、工作台和报告体验，并 MUST 明确保持 demo 来源


## ADDED Requirements

### Requirement: Analysis submission carries annotation reference
`AnalysisSubmit` SHALL 新增可选的 `normalized_annotation_id` 字段，调用方可指定使用哪份标准化标注进行分析；未提供时由 service 按规则解析当前 active annotation 并将其 ID 和 revision 固化到任务。

#### Scenario: Explicit annotation reference
- **WHEN** 调用方在 `AnalysisSubmit` 中提供 `normalized_annotation_id`
- **THEN** 系统 MUST 验证它属于该 session，并将其固化到 `task.request_payload.analysis_input.annotation_id`

#### Scenario: Implicit annotation resolution
- **WHEN** 调用方未提供 `normalized_annotation_id`
- **THEN** 系统 MUST 从 session 的 side video 解析 latest normalized annotation，将其 ID/revision 写入 `analysis_input`

### Requirement: Analysis submission supports acknowledge_quality_warnings
`AnalysisSubmit` SHALL 新增 `acknowledge_quality_warnings`（boolean）字段，调用方需显式确认接受 quality warning 才能继续。

#### Scenario: Warning without acknowledge rejected
- **WHEN** `quality.status = "warning"` 且 `acknowledge_quality_warnings = false`
- **THEN** 系统 MUST 返回 409，不创建分析任务

#### Scenario: Warning with acknowledge proceeds
- **WHEN** `quality.status = "warning"` 且 `acknowledge_quality_warnings = true`
- **THEN** 系统 MUST 创建分析任务，降级模块记入 `task.request_payload.analysis_input`

### Requirement: Analysis creation gates on annotation quality
`create_analysis_task` SHALL 在创建前检查 annotation quality。`invalid` 状态 MUST 阻止任务创建并返回 409；`warning` 状态需 `acknowledge_quality_warnings`；`valid` 正常创建。

#### Scenario: Invalid annotation returns 409
- **WHEN** `quality.status = "invalid"`
- **THEN** service MUST 抛出 `AnnotationQualityBlockedError`，route 映射为 HTTP 409，响应包含 blocking issues

#### Scenario: Valid annotation creates task normally
- **WHEN** `quality.status = "valid"`
- **THEN** 系统 MUST 正常创建分析任务

### Requirement: Quality snapshot saved at task creation
`create_analysis_task` SHALL 在创建时从 `NormalizedAnnotation.quality` 获取质量快照，写入 `task.request_payload.analysis_input.annotation_quality_snapshot`。

#### Scenario: Snapshot captures annotation revision
- **WHEN** 任务创建时 annotation revision = 4
- **THEN** `task.request_payload.analysis_input.annotation_quality_snapshot.source_revision` MUST 为 4

#### Scenario: Snapshot is immutable after creation
- **WHEN** 任务创建后 annotation 被重新解析、revision 递增
- **THEN** `task.request_payload.analysis_input` MUST 保持不变
