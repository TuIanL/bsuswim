## Why

当前 Vue 前端已经有上传、训练记录、任务、工作台和报告页面，业务后端也已经具备 session 级分析 API 雏形，但关键用户路径仍停在 demo/localStorage 或旧 `/tasks` 契约上。现在需要把浏览器、业务后端和模型服务先按真实 API 跑通，即使模型结果仍为 Mock，也要让上传视频到查看报告的端到端链路可验证。

## What Changes

- 将 Vue 前端上传页从“上传并绑定后提示下一阶段接入”改为提交真实 `POST /api/v1/analysis/submit`，拿到任务 ID 后进入任务状态或工作台流程。
- 将前端任务、工作台、报告 API 边界从旧 `/tasks` 和 task 级报告迁移到 session 级 `/analysis`、`/sessions`、`/reports` 契约。
- 补齐前端对真实任务状态的轮询、失败原因展示、完成后打开工作台和报告的导航。
- 让模型服务接收后端当前发送的 session 级 `videos[]` 请求 schema，并返回稳定 Mock 分析结果，确保后端任务可进入 `completed`。
- 补齐或调整后端需要的最小聚合接口，使前端能从任务 ID 加载工作台所需的任务、结果、训练记录视频和报告上下文。
- 保留无 `VITE_API_BASE_URL` 时的本地 demo 模式，但真实后端模式不再依赖 localStorage 完成分析任务流。
- **BREAKING** 前端真实后端模式不再调用旧 `/api/v1/tasks`、`/api/v1/tasks/{task_id}/workspace` 或 task 级 `GET /api/v1/reports/{task_id}`。

## Capabilities

### New Capabilities

- 无

### Modified Capabilities

- `swim-video-analysis-job-flow`: 将真实任务创建、状态轮询和任务管理从 backend-ready 进一步约束为实际调用 session 级后端 API。
- `swim-visual-analysis-workspace`: 约束工作台必须能从后端真实任务 ID 加载结果和 session 视频资源，而不是依赖 demo 或旧 task workspace。
- `swim-interactive-performance-report`: 约束报告页在真实后端模式下按 session 读取报告，并从完成任务导航进入。
- `backend-platform-core`: 补充前端连调所需的任务状态、任务详情或工作台聚合读取契约。
- `heavy-model-analysis-architecture`: 将模型服务 Mock 阶段的输入契约更新为 session 级 `videos[]` schema，确保业务后端调用可校验。

## Impact

- `frontend-vue/src/services/api.ts`、`frontend-vue/src/types.ts`、`frontend-vue/src/views/SessionUploadView.vue`、`frontend-vue/src/views/TasksView.vue`、`frontend-vue/src/views/WorkspaceView.vue`、`frontend-vue/src/views/ReportView.vue`、`frontend-vue/src/router.ts`
- `backend/app/api/routes/analysis.py`、`backend/app/api/routes/reports.py`、`backend/app/schemas/analysis.py`、`backend/app/services/analysis_service.py`
- `model_service/app/schemas.py`、`model_service/app/runtime.py`、`model_service/app/main.py`
- 本地开发环境需要同时启动 Vue 前端、业务后端、PostgreSQL 和模型服务，并配置 `VITE_API_BASE_URL` 与 `MODEL_SERVICE_URL`。
