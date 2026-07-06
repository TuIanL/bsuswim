# backend-platform-core Specification

## ADDED Requirements

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
