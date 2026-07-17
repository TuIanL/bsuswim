## ADDED Requirements

### Requirement: Ingestion route

系统 SHALL 提供 `POST /sessions/{session_id}/videos/{video_id}/annotations/ingest` 端点。

#### Scenario: Ingest accepts multipart fields
- **WHEN** 调用 ingest 端点
- **THEN** 请求 MUST 接受 `file`、`source`、`annotation_fps`、`metadata`、`parse_options`

#### Scenario: Ingest verifies ownership
- **WHEN** session 不属于当前用户
- **THEN** 系统 MUST 返回 404

#### Scenario: Video not bound to session
- **WHEN** video 不属于该 session
- **THEN** 系统 MUST 返回 404

### Requirement: Ingestion service

系统 SHALL 提供 `AnnotationIngestionService` 编排 upload 和 parse 流程。

#### Scenario: Service reuses existing create_annotation
- **WHEN** ingest 流程需要保存文件
- **THEN** 系统 MUST 复用 `create_annotation()` 函数

#### Scenario: Service reuses existing parse_annotation_file
- **WHEN** ingest 流程需要解析标注
- **THEN** 系统 MUST 复用 `parse_annotation_file()` 函数

#### Scenario: Service does not call route functions
- **WHEN** 编排 upload 和 parse
- **THEN** service MUST NOT 直接调用 route 层的函数

### Requirement: derive_analysis_readiness is shared

`derive_analysis_readiness()` SHALL 从 route 模块移至共享模块，供 parse、ingest、validate、list 复用。

#### Scenario: Readiness computed outside route
- **WHEN** 任意入口需要 readiness 信息
- **THEN** 系统 MUST 从共享位置调用 `derive_analysis_readiness()`
