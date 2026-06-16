## ADDED Requirements

### Requirement: Platform technology stack
系统 SHALL 使用确定的 Web 分析平台技术栈实现真实游泳视频分析能力。

#### Scenario: Frontend stack is used
- **WHEN** 实现前端分析平台
- **THEN** 系统 MUST 使用 Vue3、TypeScript、Vite、Element Plus、ECharts、Pinia、Axios、原生 `video` 和 Canvas 作为主技术栈

#### Scenario: Backend stack is used
- **WHEN** 实现业务后端
- **THEN** 系统 MUST 使用 FastAPI、Pydantic、SQLAlchemy 和 MySQL 管理业务 API、数据校验、ORM 和持久化数据

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
- **WHEN** 用户提交有效视频和游泳训练元数据
- **THEN** 系统 MUST 保存视频记录并创建状态为 `uploaded` 或 `queued` 的分析任务记录

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
