# swim-video-analysis-job-flow Specification (Delta)

## ADDED Requirements

### Requirement: Analysis submission carries annotation reference
`AnalysisSubmit` SHALL 新增可选的 `normalized_annotation_id` 字段，调用方可指定使用哪份标准化标注进行分析；未提供时由 service 按规则解析当前 active annotation 并将其 ID 和 revision 固化到任务。

#### Scenario: Explicit annotation reference
- **WHEN** 调用方在 `AnalysisSubmit` 中提供 `normalized_annotation_id`
- **THEN** 系统 MUST 验证它属于该 session，并将其固化到 `task.request_payload.analysis_input.annotation_id`

#### Scenario: Implicit annotation resolution
- **WHEN** 调用方未提供 `normalized_annotation_id`
- **THEN** 系统 MUST 从 session 的 side video 解析 latest normalized annotation，将其 ID/revision 写入 `analysis_input`

### Requirement: Analysis submission supports acknowledge_quality_warnings
`AnalysisSubmit` SHALL 新增 `acknowledge_quality_warnings`（boolean）字段，调用方需显式确认接受 quality warning 才能继续。

#### Scenario: Warning without acknowledge rejected
- **WHEN** `quality.status = "warning"` 且 `acknowledge_quality_warnings = false`
- **THEN** 系统 MUST 返回 409，不创建分析任务

#### Scenario: Warning with acknowledge proceeds
- **WHEN** `quality.status = "warning"` 且 `acknowledge_quality_warnings = true`
- **THEN** 系统 MUST 创建分析任务，降级模块记入 `task.request_payload.analysis_input`

### Requirement: Analysis creation gates on annotation quality
`create_analysis_task` SHALL 在创建前检查 annotation quality。`invalid` 状态 MUST 阻止任务创建并返回 409；`warning` 状态需 `acknowledge_quality_warnings`；`valid` 正常创建。

#### Scenario: Invalid annotation returns 409
- **WHEN** `quality.status = "invalid"`
- **THEN** service MUST 抛出 `AnnotationQualityBlockedError`，route 映射为 HTTP 409，响应包含 blocking issues

#### Scenario: Valid annotation creates task normally
- **WHEN** `quality.status = "valid"`
- **THEN** 系统 MUST 正常创建分析任务

### Requirement: Quality snapshot saved at task creation
`create_analysis_task` SHALL 在创建时从 `NormalizedAnnotation.quality` 获取质量快照，写入 `task.request_payload.analysis_input.annotation_quality_snapshot`。

#### Scenario: Snapshot captures annotation revision
- **WHEN** 任务创建时 annotation revision = 4
- **THEN** `task.request_payload.analysis_input.annotation_quality_snapshot.source_revision` MUST 为 4

#### Scenario: Snapshot is immutable after creation
- **WHEN** 任务创建后 annotation 被重新解析、revision 递增
- **THEN** `task.request_payload.analysis_input` MUST 保持不变
