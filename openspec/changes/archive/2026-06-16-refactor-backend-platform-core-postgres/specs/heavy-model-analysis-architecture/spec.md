## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: Session-level model dispatch
业务后端 SHALL 基于训练记录聚合运动员、训练上下文和绑定视频后调用独立模型服务。

#### Scenario: Backend dispatches session analysis
- **WHEN** session 级分析任务开始处理
- **THEN** 业务后端 MUST 向模型服务发送包含 `task_id`、`session_id`、运动员信息、训练记录信息、视频列表和 schema version 的请求

#### Scenario: Session has multiple videos
- **WHEN** 训练记录绑定了多个机位视频
- **THEN** 业务后端 MUST 在模型请求中保留每个视频的机位类型、播放引用或路径、帧率和同步偏移信息
