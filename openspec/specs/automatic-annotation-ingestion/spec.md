## ADDED Requirements

### Requirement: One-step annotation ingestion

系统 SHALL 支持通过一个高层接口完成原始标注上传、解析、质量检查和 readiness 计算。

#### Scenario: Valid CVAT annotation is ingested
- **WHEN** 用户向 `POST /sessions/{session_id}/videos/{video_id}/annotations/ingest` 上传有效 CVAT XML
- **THEN** 系统 MUST 创建 AnnotationFile
- **AND** 解析为 NormalizedAnnotation
- **AND** 执行质量检查
- **AND** 返回 `normalized_annotation_id`
- **AND** 返回 `revision`、`summary`、`quality`、`analysis_readiness`

### Requirement: Parsed and quality-valid are separate states

AnnotationFile.status SHALL 与 quality.status 独立。

#### Scenario: Structurally parsed but analytically invalid
- **WHEN** 文件成功转换为 NormalizedAnnotation 但 quality.status 为 invalid
- **THEN** AnnotationFile.status MUST 为 parsed
- **AND** analysis_readiness.can_submit MUST 为 false
- **AND** 系统 MUST 返回成功响应而非 parse_failed

### Requirement: Parse failure preserves uploaded input

解析失败后系统 SHALL 保留原始文件。

#### Scenario: Parse fails after file saved
- **WHEN** 文件已保存但 parser 返回错误
- **THEN** AnnotationFile.status MUST 为 parse_failed
- **AND** parse_error MUST 被保存
- **AND** 原始文件 MUST 保留
- **AND** 错误响应 MUST 包含 annotation_file_id
- **AND** 用户 MUST 能通过 POST .../parse 重试

### Requirement: Ingestion result is reloadable

摄取结果 SHALL 不依赖单次 HTTP 响应，且标注列表响应 SHALL 提供刷新后恢复解析摘要、质量详情与四类模块可用状态所需的数据。

#### Scenario: Page reload after successful ingestion
- **WHEN** 用户刷新上传页面
- **THEN** 列表响应 MUST 返回 `normalized_annotation_id`
- **AND** 返回 `normalized_revision`
- **AND** 返回 `quality_status`
- **AND** 返回 `analysis_readiness`
- **AND** 返回持久化的 `parse_summary`
- **AND** 返回完整的 `quality` 报告
- **AND** 返回 `kinematics_module_readiness`（body_posture / upper_limb / lower_limb / head_trunk，状态为 ready|degraded|blocked）
- **AND** 返回持久化的 parse warnings

### Requirement: Standard UI uses ingestion exclusively

普通前端标注上传流程 SHALL 仅使用 ingest 端点。

#### Scenario: Upload button replaced
- **WHEN** 用户选择文件并点击上传
- **THEN** 前端 MUST 调用 `POST .../annotations/ingest`
- **AND** MUST NOT 拆分为 upload + parse 两次调用
