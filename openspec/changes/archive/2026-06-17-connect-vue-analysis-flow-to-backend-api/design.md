## Context

当前系统已经完成从单视频任务向训练记录 session 级任务的后端模型迁移：业务后端提供 `/api/v1/videos`、`/sessions`、`/analysis` 和 `/reports`，并会在创建任务后通过 `BackgroundTasks` 调用独立模型服务。Vue 前端也已经有创建训练记录、多机位上传、任务列表、工作台和报告页面。

缺口在于这些模块尚未形成真实端到端链路：上传页提交分析仍停留在提示文案，前端 API 边界仍残留旧 `/tasks` 契约，工作台和报告页仍以 task 级 report/workspace 为中心；同时业务后端发送给模型服务的是 session 级 `videos[]` schema，而模型服务仍按旧单视频 schema 校验请求。结果是“浏览器、业务后端、模型服务三者一起跑通”尚不可验证。

## Goals / Non-Goals

**Goals:**

- 让 Vue 前端在配置 `VITE_API_BASE_URL` 时通过真实 REST API 完成上传视频、绑定训练记录、提交分析、轮询状态、打开工作台和查看报告。
- 让模型服务在 Mock 阶段接收业务后端当前的 session 级请求 schema，并返回可保存、可生成报告的稳定结果。
- 明确前端真实后端模式下的 ID 语义：`task_id` 用于分析状态和结果，`session_id` 用于训练记录、绑定视频和报告。
- 保留 demo 模式，使无后端配置时仍可演示本地样例数据。
- 补齐后端前端连调所需的最小读取接口或聚合响应，避免前端继续调用不存在的旧 `/tasks`。

**Non-Goals:**

- 不在本次引入真实 YOLO、姿态估计或视频帧级重模型推理。
- 不引入 Celery、Redis 队列执行或 MinIO 对象存储。
- 不实现 PDF 导出。
- 不重做整体 UI 视觉设计，也不重构非 Vue 的旧 Next.js 演示前端。
- 不改变已有注册、登录、运动员和训练记录的核心业务模型。

## Decisions

### 以前端 API 边界统一迁移为 session/task 双 ID

真实后端模式下，前端服务层不再暴露旧 `createAnalysisTask(videoId, metadata)`、`getWorkspace(taskId)` 打 `/tasks` 的语义，而是提供：

- `submitAnalysis(sessionId)` 调用 `POST /api/v1/analysis/submit`
- `getAnalysisStatus(taskId)` 调用 `GET /api/v1/analysis/{task_id}/status`
- `getAnalysisResult(taskId)` 调用 `GET /api/v1/analysis/{task_id}/result`
- `getReport(sessionId)` 调用 `GET /api/v1/reports/{session_id}`
- 必要时 `generateReport(sessionId)` 调用 `POST /api/v1/reports/generate`

选择这个方向是因为后端已经把训练记录作为业务聚合根，报告也已经是 session 级。替代方案是保留前端旧 task 级包装，由后端新增兼容 `/tasks` 路由；这会短期少改前端，但会延长旧 `video_id` 任务模型的寿命。

### 工作台从任务 ID 加载，报告从 session ID 加载

路由可以继续保留 `/workspace/:taskId`，因为用户从任务状态进入工作台时自然持有 `task_id`；工作台通过任务状态或任务详情获得 `session_id`，再加载绑定视频和结果。报告页应改为 `/reports/:sessionId` 或在打开时明确用 `session_id` 请求后端报告。

这样可以避免报告 API 在 task 级和 session 级之间摇摆。替代方案是在报告路由继续叫 `taskId`，页面内部再查 session；这会降低 URL 语义清晰度，也容易继续误调 `GET /reports/{task_id}`。

### 模型服务升级到 session 级 Mock schema

模型服务第一步不做真实推理，但必须接受后端 `ModelAnalysisRequest` 的字段：`task_id`、`session_id`、`athlete`、`session`、`videos[]`、`callback_url` 和 `schema_version`。Mock runtime 使用这些输入生成稳定 `swim-analysis.v1` 响应，保证业务后端可以保存 `AnalysisResult` 并生成报告。

替代方案是在业务后端把 session 请求降级成旧单视频 `video_path/video_url/metadata` schema；这会掩盖多机位和 session 级任务的真实接口问题，后续接入真实模型时还要再迁移一次。

### 后端只补最小连调接口

如果现有后端缺少前端所需读取能力，应优先补 `/api/v1/analysis/{task_id}` 或 `/api/v1/analysis/{task_id}/workspace` 这类最小聚合接口，返回任务、结果、训练记录和绑定视频摘要。不要恢复旧 `/api/v1/tasks` 作为正式接口。

替代方案是让前端组合多次请求拼装工作台数据。这可以减少后端改动，但会把业务聚合逻辑分散到页面里；本次可以在服务层组合，但如果页面需要多处复用，应沉到后端聚合接口。

## Risks / Trade-offs

- 真实后端模式需要登录 token、PostgreSQL、业务后端和模型服务同时可用 → 在任务中加入本地连调步骤，并确保错误信息能区分未登录、后端不可达、模型服务失败和报告未生成。
- FastAPI `BackgroundTasks` 只能覆盖 MVP，本地服务重启会中断执行 → 继续依赖数据库任务状态，并保留后续迁移 Celery + Redis 的接口兼容边界。
- Mock 结果可能被误认为真实模型输出 → 报告和工作台必须显示来源为 Mock 或 model service simulated，且不得暗示真实 YOLO 已接入。
- 多机位结果与单视频 Canvas 叠加可能不完全匹配 → 工作台第一版选择一个默认主视频展示，同时保留机位来源和受限状态。
- 前端 demo 模式和真实模式类型差异可能造成条件分支复杂 → 类型层同时表达 `session_id`、可选 `request_payload`、可选 demo 字段，并把模式差异封装在 service 层。

## Migration Plan

1. 更新模型服务请求 schema 和 Mock runtime，使业务后端现有 `ModelServiceClient` 调用可以成功。
2. 补齐后端分析任务读取或工作台聚合 API，并确认报告生成在任务完成后可直接读取或可按需生成。
3. 更新 Vue 类型和 API service，保留 demo 分支，真实分支迁移到 `/analysis`、`/sessions`、`/reports`。
4. 更新上传页、任务页、工作台和报告页的导航与状态处理。
5. 本地启动 PostgreSQL、业务后端、模型服务和 Vue 前端，执行注册/登录、创建运动员、创建训练记录、上传视频、提交分析、轮询完成、查看工作台、查看报告的浏览器连调。

回滚策略：如果模型服务 schema 升级阻塞，可临时在模型服务中同时接受旧单视频 schema 和新 session schema，但前端真实模式不应回退到旧 `/tasks` 契约。
