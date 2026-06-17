## ADDED Requirements

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
