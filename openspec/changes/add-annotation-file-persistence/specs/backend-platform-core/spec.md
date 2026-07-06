# backend-platform-core Specification

## ADDED Requirements

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
