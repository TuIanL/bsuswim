# backend-platform-core Specification

## Purpose
TBD - created by archiving change refactor-backend-platform-core-postgres. Update Purpose after archive.
## Requirements
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

### Requirement: Analysis task detail API for frontend integration
业务后端 SHALL 提供前端连调所需的分析任务读取能力，使 Vue 前端能从 `task_id` 获得任务所属训练记录和可用操作。

#### Scenario: Frontend reads analysis task detail
- **WHEN** 已登录调用方请求真实分析任务详情或正式 analysis workspace 聚合 API
- **THEN** 系统 MUST 返回任务 ID、训练记录 ID、状态、阶段、进度、错误信息、时间戳和可用操作

#### Scenario: Unauthorized task is requested
- **WHEN** 调用方请求不属于当前用户可访问训练记录的分析任务
- **THEN** 系统 MUST 返回稳定的未找到或未授权错误，不得泄露其他用户任务数据

### Requirement: Analysis workspace data contract
业务后端 SHALL 支持前端加载真实工作台所需的数据组合。

#### Scenario: Workspace data is requested for completed task
- **WHEN** 已登录调用方请求已完成任务的工作台数据
- **THEN** 系统 MUST 返回任务状态、分析结果、训练记录 ID 和该训练记录已绑定视频的文件摘要与播放 URL

#### Scenario: Workspace data is requested before result exists
- **WHEN** 已登录调用方请求尚未完成或没有结果的任务工作台数据
- **THEN** 系统 MUST 返回任务状态和训练记录上下文，并以空结果或稳定错误表达结果尚不可用

### Requirement: Completed analysis exposes session report path
业务后端 SHALL 保证完成的分析任务可以关联到 session 级报告读取。

#### Scenario: Model result is saved for a task
- **WHEN** 后端保存模型服务返回的有效分析结果并将任务更新为 `completed`
- **THEN** 系统 MUST 创建或刷新该任务所属训练记录的报告元数据，使 `GET /api/v1/reports/{session_id}` 可读取报告

#### Scenario: Report generation fails after result save
- **WHEN** 分析结果已保存但报告生成失败
- **THEN** 系统 MUST 保留任务完成或失败状态的一致性，并返回可读错误用于前端展示或重试生成报告

### Requirement: Annotation file persistence APIs
业务后端 SHALL 扩展核心 API，支持标注文件的上传、查询、下载和归档操作。

#### Scenario: Annotation upload endpoint registered
- **WHEN** 后端应用启动
- **THEN** 系统 MUST 注册 `POST /api/v1/sessions/{session_id}/videos/{video_id}/annotations` 端点，接受 multipart/form-data 格式的标注文件上传

#### Scenario: Annotation list endpoint registered
- **WHEN** 后端应用启动
- **THEN** 系统 MUST 注册 `GET /api/v1/sessions/{session_id}/videos/{video_id}/annotations` 端点

#### Scenario: Annotation detail endpoint registered
- **WHEN** 后端应用启动
- **THEN** 系统 MUST 注册 `GET /api/v1/annotations/{annotation_file_id}` 端点，并纳入 API router

#### Scenario: Annotation download endpoint registered
- **WHEN** 后端应用启动
- **THEN** 系统 MUST 注册 `GET /api/v1/annotations/{annotation_file_id}/download` 端点

#### Scenario: Annotation archive endpoint registered
- **WHEN** 后端应用启动
- **THEN** 系统 MUST 注册 `POST /api/v1/annotations/{annotation_file_id}/archive` 端点

### Requirement: Annotation file database schema
业务后端 SHALL 新增 `annotation_files` 表并通过 Alembic 管理其 schema 演进。

#### Scenario: Annotation files table created
- **WHEN** 开发者对数据库执行 annotation file migration
- **THEN** 系统 MUST 创建 `annotation_files` 表，包含 `session_video_id` 外键引用 `session_videos.id`、`source` 和 `status` 的 PostgreSQL ENUM 约束、以及 `session_video_id + source + version` 唯一约束

#### Scenario: Existing platform tables unaffected
- **WHEN** 执行 annotation file migration
- **THEN** 系统 MUST 不修改现有 `training_sessions`、`video_files`、`session_videos`、`analysis_tasks`、`analysis_results`、`report_metadata` 表结构

### Requirement: Normalized annotation API endpoints
业务后端 SHALL 扩展核心 API，注册标准化标注的创建、查询和列表端点。

#### Scenario: Create normalized annotation endpoint registered
- **WHEN** 后端应用启动
- **THEN** 系统 MUST 注册 `POST /api/v1/session-videos/{session_video_id}/normalized-annotations` 端点

#### Scenario: Parse annotation file endpoint registered
- **WHEN** 后端应用启动
- **THEN** 系统 MUST 注册 `POST /api/v1/annotations/{annotation_file_id}/parse` 端点

#### Scenario: Get normalized annotation endpoint registered
- **WHEN** 后端应用启动
- **THEN** 系统 MUST 注册 `GET /api/v1/normalized-annotations/{normalized_annotation_id}` 端点

#### Scenario: List normalized annotations endpoint registered
- **WHEN** 后端应用启动
- **THEN** 系统 MUST 注册 `GET /api/v1/session-videos/{session_video_id}/normalized-annotations` 端点

### Requirement: Normalized annotations database schema
业务后端 SHALL 新增 `normalized_annotations` 表并通过 Alembic 管理 schema 演进。

#### Scenario: Normalized annotations table created
- **WHEN** 开发者对数据库执行 normalized annotation migration
- **THEN** 系统 MUST 创建 `normalized_annotations` 表，包含 `session_video_id` 外键引用 `session_videos.id`、`annotation_file_id` 可空外键引用 `annotation_files.id` 及 UNIQUE 约束、`revision` 字段默认值 1、以及 events/keypoint_frames/trajectories/manual_tags/scale/coordinate_system/quality 的 JSONB 列

#### Scenario: Existing platform tables unaffected
- **WHEN** 执行 normalized annotation migration
- **THEN** 系统 MUST 不修改 `analysis_results`、`report_metadata` 等现有表结构

