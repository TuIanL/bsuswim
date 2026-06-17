## 1. 模型服务 Mock 契约

- [x] 1.1 更新 `model_service` 请求 schema，使 `/api/v1/analyze` 接收 `task_id`、`session_id`、`athlete`、`session`、`videos[]`、`callback_url` 和 `schema_version`
- [x] 1.2 更新 Mock runtime，基于 session 级请求返回 `swim-analysis.v1` 的 metrics、diagnostics、phases、detections 或 keypoint_frames
- [x] 1.3 验证业务后端 `ModelAnalysisRequest` 发送到模型服务后能通过模型服务和后端 `ModelAnalysisResult` 双方校验

## 2. 后端分析读取与报告链路

- [x] 2.1 补齐分析任务详情或 workspace 聚合 API，返回任务状态、`session_id`、错误信息、可用操作、分析结果和 session 视频摘要
- [x] 2.2 确认 `save_analysis_result` 在任务完成时创建或刷新 session 级报告元数据，使 `GET /api/v1/reports/{session_id}` 可直接读取
- [x] 2.3 为未完成任务、无结果任务、越权任务和报告未生成状态返回稳定错误或空结果契约
- [x] 2.4 添加或更新后端测试，覆盖提交分析、模型 Mock 返回、任务完成、结果读取和报告读取

## 3. Vue API 与类型迁移

- [x] 3.1 更新 `frontend-vue/src/types.ts`，让 `AnalysisTask`、`WorkspaceData`、`ReportData` 表达 `session_id`、后端状态和 session 级报告字段
- [x] 3.2 更新 `frontend-vue/src/services/api.ts`，新增或替换为 `submitAnalysis`、`getAnalysisStatus`、`getAnalysisResult`、`getAnalysisWorkspace`、`getReport(sessionId)`、`generateReport(sessionId)`
- [x] 3.3 移除真实后端模式下对旧 `/tasks`、`/tasks/{task_id}/workspace` 和 task 级 `/reports/{task_id}` 的调用
- [x] 3.4 保留 demo mode 分支，使无 `VITE_API_BASE_URL` 时现有 demo 页面仍可运行并标识 demo 来源

## 4. Vue 页面任务流接入

- [x] 4.1 更新 `SessionUploadView.vue`，在至少一个视频绑定成功后调用 `submitAnalysis(sessionId)`，成功后导航到真实任务状态或工作台入口
- [x] 4.2 更新 `TasksView.vue`，展示训练记录和真实分析任务状态、进度、失败原因，并按状态启用上传、工作台和报告操作
- [x] 4.3 更新 `WorkspaceView.vue`，基于 `task_id` 轮询状态、加载结果和 session 视频，完成后启用 session 报告导航
- [x] 4.4 更新 `ReportView.vue` 和路由参数语义，使真实后端模式按 `session_id` 请求报告并处理报告未就绪状态
- [x] 4.5 确认页面错误提示能区分未登录、后端不可达、模型失败、任务未完成和报告未生成

## 5. 端到端验证

- [x] 5.1 启动 PostgreSQL、业务后端、模型服务和 Vue 前端，并配置 `VITE_API_BASE_URL` 与 `MODEL_SERVICE_URL`
- [x] 5.2 在浏览器完成注册或登录、创建运动员、创建训练记录、上传视频、绑定 session video、提交分析的真实流程
- [x] 5.3 验证任务状态从 queued/processing 进入 completed，且失败时能显示后端错误原因
- [x] 5.4 验证工作台能打开真实任务、加载视频资源和 Mock 结果指标
- [x] 5.5 验证报告页按 `session_id` 展示后端生成报告，并清晰标识 Mock 或模拟来源
- [x] 5.6 运行相关前端构建、类型检查和后端测试，记录任何未覆盖或受限的验证项
