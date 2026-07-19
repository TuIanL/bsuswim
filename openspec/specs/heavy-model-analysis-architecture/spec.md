# heavy-model-analysis-architecture Specification

## Purpose

约束重模型游泳视频分析平台的前后端技术栈、文件存储、模型服务隔离、异步任务状态、Mock 到真实推理的演进边界，以及报告生成链路。
## Requirements
### Requirement: Platform technology stack
系统 SHALL 使用确定的 Web 分析平台技术栈实现真实游泳视频分析能力。

#### Scenario: Frontend stack is used
- **WHEN** 实现前端分析平台
- **THEN** 系统 MUST 使用 Vue3、TypeScript、Vite、Element Plus、ECharts、Pinia、Axios、原生 `video` 和 Canvas 作为主技术栈

#### Scenario: Backend stack is used
- **WHEN** 实现业务后端
- **THEN** 系统 MUST 使用 FastAPI、Pydantic、SQLAlchemy 和 PostgreSQL 管理业务 API、数据校验、ORM 和持久化数据

#### Scenario: Backend schema changes are introduced
- **WHEN** 业务后端新增或调整持久化表结构
- **THEN** 系统 MUST 使用 Alembic migration 管理 schema 变更

### Requirement: Separate heavy model service
系统 SHALL 将 YOLO 类重模型推理和业务后端隔离到独立模型服务。

#### Scenario: Backend dispatches model analysis
- **WHEN** 业务后端需要分析已上传视频
- **THEN** 业务后端 MUST 通过内部 API 调用独立 FastAPI 模型服务，而不是在业务后端进程中直接加载 YOLO 类模型

#### Scenario: Model service returns structured result
- **WHEN** 模型服务完成视频分析
- **THEN** 模型服务 MUST 返回包含 `schema_version`、检测结果、关键点或骨架数据、指标结果、诊断线索和错误信息的结构化响应

### Requirement: Persistent analysis task state
系统 SHALL 将视频分析任务状态持久化到数据库。

#### Scenario: Analysis task is created
- **WHEN** 用户提交有效训练记录和已绑定的游泳视频资源
- **THEN** 系统 MUST 保存训练记录视频关系并创建状态为 `uploaded` 或 `queued` 的 session 级分析任务记录

#### Scenario: Task continues after refresh
- **WHEN** 用户刷新浏览器或重新打开任务列表
- **THEN** 系统 MUST 从后端 API 返回数据库中的任务状态、进度、更新时间和可用操作

#### Scenario: Model analysis fails
- **WHEN** 模型服务调用、视频处理或结果保存失败
- **THEN** 系统 MUST 将任务标记为 `failed`，保存可读错误原因，并允许前端展示稳定错误状态

### Requirement: Local upload storage with future object storage boundary
系统 SHALL 使用本地 `uploads` 作为 MVP 文件存储，并保留迁移到 MinIO 的存储边界。

#### Scenario: Video file is uploaded
- **WHEN** 用户上传支持的视频文件
- **THEN** 系统 MUST 将文件保存到本地 `uploads`，并在数据库中记录文件名、存储路径或对象键、大小、MIME type 和上传时间

#### Scenario: Storage backend changes later
- **WHEN** 文件存储从本地 `uploads` 迁移到 MinIO
- **THEN** 业务 API 和前端任务流程 MUST 继续使用视频资源引用，不要求调用方依赖本地绝对路径

### Requirement: HTML report generation from analysis result
系统 SHALL 基于真实分析结果生成 HTML 报告页。

#### Scenario: Completed task has result
- **WHEN** 分析任务状态为 `completed`
- **THEN** 系统 MUST 提供报告数据 API，用于展示训练摘要、关键指标、技术诊断、可视化图表和训练建议

#### Scenario: PDF export is unavailable
- **WHEN** 第一版系统尚未实现 PDF 导出
- **THEN** 系统 MUST 仍然提供完整 HTML 报告页，并且不得把 PDF 导出展示为可用能力

### Requirement: Upgrade path for production async execution
系统 SHALL 保持从 `BackgroundTasks` 到 Celery + Redis 的迁移路径。

#### Scenario: MVP background execution runs
- **WHEN** 后端创建分析任务
- **THEN** 系统 MAY 使用 FastAPI `BackgroundTasks` 启动异步分析，但任务状态 MUST 由数据库记录

#### Scenario: Queue backend is upgraded
- **WHEN** 系统迁移到 Celery + Redis
- **THEN** 前端 API 契约、任务状态字段和报告读取方式 MUST 保持兼容

### Requirement: Session-level model dispatch
业务后端 SHALL 基于训练记录聚合运动员、训练上下文和绑定视频后调用独立模型服务。

#### Scenario: Backend dispatches session analysis
- **WHEN** session 级分析任务开始处理
- **THEN** 业务后端 MUST 向模型服务发送包含 `task_id`、`session_id`、运动员信息、训练记录信息、视频列表和 schema version 的请求

#### Scenario: Session has multiple videos
- **WHEN** 训练记录绑定了多个机位视频
- **THEN** 业务后端 MUST 在模型请求中保留每个视频的机位类型、播放引用或路径、帧率和同步偏移信息

### Requirement: Mock model service accepts session analysis requests
Mock 阶段的模型服务 SHALL 接收业务后端发送的 session 级分析请求 schema。

#### Scenario: Backend sends session-level model request
- **WHEN** 业务后端向模型服务 `POST /api/v1/analyze` 发送包含 `task_id`、`session_id`、运动员信息、训练记录信息、`videos[]`、`callback_url` 和 `schema_version` 的请求
- **THEN** 模型服务 MUST 成功校验该请求，并不得要求旧单视频 `video_path`、`video_url` 和 `metadata` 顶层字段

#### Scenario: Request includes multiple videos
- **WHEN** 请求中的 `videos[]` 包含多个机位视频
- **THEN** 模型服务 MUST 保留或可读取每个视频的 `video_file_id`、`view_type`、`video_path`、`video_url`、`fps`、`resolution` 和 `sync_offset_ms`

### Requirement: Mock model service returns saveable swim result
Mock 阶段的模型服务 SHALL 返回业务后端可保存并可生成报告的稳定游泳分析结果。

#### Scenario: Mock inference completes
- **WHEN** 模型服务收到有效 session 级分析请求
- **THEN** 模型服务 MUST 返回 `status=completed`、`schema_version=swim-analysis.v1`、指标、诊断、阶段或关键点相关结构化字段

#### Scenario: Backend validates model response
- **WHEN** 业务后端使用 `ModelAnalysisResult` 校验模型服务响应
- **THEN** 响应 MUST 通过校验，并允许后端保存 `AnalysisResult`、更新任务为 `completed`、生成 session 报告

### Requirement: Mock provenance is explicit
模型服务 Mock 输出 SHALL 可被前端和报告识别为模拟分析结果。

#### Scenario: Mock result is transformed into report
- **WHEN** 后端基于 Mock 模型服务响应生成报告数据
- **THEN** 报告或结果来源 MUST 能标识为模型服务 Mock、模拟或非真实重模型推理

### Requirement: Analysis tasks support multiple pipeline types

AnalysisTask SHALL 不再只代表模型服务任务，执行器 SHALL 根据 pipeline_type 路由。

#### Scenario: Pipeline routing

- **WHEN** AnalysisTask 被创建
- **THEN** 系统 SHALL 持久化 pipeline_type 和 pipeline_version
- **AND** 执行器 SHALL 根据 pipeline_type 选择执行路径
- **AND** model_service pipeline 行为 SHALL 保持独立，不加载重模型

#### Scenario: Legacy model-service failure semantics remain isolated

- **WHEN** model_service pipeline 失败
- **THEN** 系统 SHALL 继续使用既有 `_set_task_state` 与 `_mark_failed` 行为
- **AND** 新增的结构化执行字段（execution_state / failed_stage / error_code）
      对于 model_service 任务 MAY 保持为空
- **AND** annotation_kinematics pipeline 的 checkpoint-aware 失败写入器
       MUST NOT 修改或重定义 `_mark_failed`
