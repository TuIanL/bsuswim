## ADDED Requirements

### Requirement: PostgreSQL backend runtime
业务后端 SHALL 默认使用 PostgreSQL 作为持久化数据库，并提供本地开发所需的数据库配置入口。

#### Scenario: Backend uses PostgreSQL database URL
- **WHEN** 后端在默认开发配置下启动
- **THEN** 系统 MUST 使用 PostgreSQL SQLAlchemy URL 连接业务数据库，而不是 MySQL URL

#### Scenario: Local database services are started
- **WHEN** 开发者启动本地依赖服务
- **THEN** 系统 MUST 提供 PostgreSQL 服务配置，并保留 Redis 和 MinIO 作为后续队列与对象存储扩展边界

### Requirement: Alembic managed schema
业务后端 SHALL 使用 Alembic 管理平台核心表结构和后续 schema 演进。

#### Scenario: Database schema is initialized
- **WHEN** 开发者对空 PostgreSQL 数据库执行 migration
- **THEN** 系统 MUST 创建用户、队伍、运动员、训练记录、视频文件、训练记录视频绑定、分析任务、分析结果和报告元数据相关表

#### Scenario: Backend application starts
- **WHEN** 后端应用进程启动
- **THEN** 系统 MUST 不依赖应用启动时自动 `create_all` 来管理正式数据库表结构

### Requirement: Authenticated user APIs
业务后端 SHALL 提供第一版 JWT 认证 API，用于注册、登录和读取当前用户。

#### Scenario: Coach registers an account
- **WHEN** 调用方提交有效的注册信息到 `POST /api/v1/auth/register`
- **THEN** 系统 MUST 创建可登录用户，保存哈希后的密码，并返回不包含密码哈希的用户信息

#### Scenario: User logs in
- **WHEN** 调用方提交正确账号和密码到 `POST /api/v1/auth/login`
- **THEN** 系统 MUST 返回 Bearer access token

#### Scenario: User reads current profile
- **WHEN** 已登录调用方携带有效 Bearer token 请求 `GET /api/v1/users/me`
- **THEN** 系统 MUST 返回当前用户信息

### Requirement: Athlete profile APIs
业务后端 SHALL 提供运动员档案 API，并将运动员归属到当前教练或用户上下文。

#### Scenario: Coach creates an athlete
- **WHEN** 已登录教练向 `POST /api/v1/athletes` 提交有效运动员档案
- **THEN** 系统 MUST 创建运动员记录，并将其关联到当前用户

#### Scenario: Coach lists owned athletes
- **WHEN** 已登录教练请求 `GET /api/v1/athletes`
- **THEN** 系统 MUST 返回当前用户可访问的运动员列表

#### Scenario: Coach reads athlete detail
- **WHEN** 已登录教练请求 `GET /api/v1/athletes/{athlete_id}`
- **THEN** 系统 MUST 仅在该运动员可被当前用户访问时返回档案详情

### Requirement: Training session APIs
业务后端 SHALL 以训练记录作为运动员、视频、分析任务和报告之间的业务中心。

#### Scenario: Coach creates a training session
- **WHEN** 已登录教练向 `POST /api/v1/sessions` 提交有效训练记录，并引用可访问的运动员
- **THEN** 系统 MUST 创建训练记录并关联运动员与当前用户

#### Scenario: Coach lists training sessions
- **WHEN** 已登录教练请求 `GET /api/v1/sessions`
- **THEN** 系统 MUST 返回当前用户可访问的训练记录列表

#### Scenario: Coach lists sessions for one athlete
- **WHEN** 已登录教练请求 `GET /api/v1/athletes/{athlete_id}/sessions`
- **THEN** 系统 MUST 返回该运动员下当前用户可访问的训练记录列表

### Requirement: Session video binding APIs
业务后端 SHALL 将上传的视频文件通过业务关系绑定到训练记录，并记录机位与同步信息。

#### Scenario: Video file is uploaded
- **WHEN** 调用方上传有效视频到 `POST /api/v1/videos/upload`
- **THEN** 系统 MUST 保存视频文件并创建 `video_files` 记录

#### Scenario: Video is bound to a session
- **WHEN** 已登录调用方向 `POST /api/v1/sessions/{session_id}/videos` 提交 `video_file_id` 和机位信息
- **THEN** 系统 MUST 创建 `session_videos` 记录，而不是把机位信息直接写入 `video_files`

#### Scenario: Session videos are listed
- **WHEN** 已登录调用方请求 `GET /api/v1/sessions/{session_id}/videos`
- **THEN** 系统 MUST 返回该训练记录绑定的视频文件及其业务角色信息

### Requirement: Session-level analysis APIs
业务后端 SHALL 提供以训练记录为输入的 AI 分析 API。

#### Scenario: Analysis is submitted for a session
- **WHEN** 已登录调用方向 `POST /api/v1/analysis/submit` 提交有效 `session_id`
- **THEN** 系统 MUST 创建引用该训练记录的分析任务，并基于训练记录、运动员和已绑定视频组装模型服务请求

#### Scenario: Analysis status is queried
- **WHEN** 调用方请求 `GET /api/v1/analysis/{task_id}/status`
- **THEN** 系统 MUST 返回任务 ID、训练记录 ID、状态、进度、阶段、错误信息和时间戳

#### Scenario: Analysis result is saved
- **WHEN** 模型服务或后端流程向 `POST /api/v1/analysis/{task_id}/result` 提交有效结果
- **THEN** 系统 MUST 保存结构化分析结果，并将任务更新为对应终态

#### Scenario: Analysis result is read
- **WHEN** 调用方请求 `GET /api/v1/analysis/{task_id}/result`
- **THEN** 系统 MUST 返回该任务已保存的结构化分析结果，或在结果不存在时返回稳定错误状态

### Requirement: Session-level report APIs
业务后端 SHALL 基于训练记录和已保存分析结果生成并读取报告数据。

#### Scenario: Report is generated for a session
- **WHEN** 已登录调用方向 `POST /api/v1/reports/generate` 提交已完成分析的 `session_id`
- **THEN** 系统 MUST 生成关联该训练记录的报告数据

#### Scenario: Report is read by session
- **WHEN** 调用方请求 `GET /api/v1/reports/{session_id}`
- **THEN** 系统 MUST 返回该训练记录的报告数据、来源和生成时间
