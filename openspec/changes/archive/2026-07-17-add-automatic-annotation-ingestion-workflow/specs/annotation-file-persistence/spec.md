## MODIFIED Requirements

### Requirement: Annotation file list includes ingestion state

`AnnotationFileListItem` SHALL 包含 `normalized_annotation_id`、`quality_status`、`analysis_readiness`、`parse_warnings` 和 `parse_error`，以便前端从列表响应中恢复摄取结果。

#### Scenario: List returns normalized annotation identity
- **WHEN** 前端请求视频的标注文件列表
- **THEN** 每个 parsed 文件的列表项 MUST 包含 `normalized_annotation_id`
- **AND** 包含 `quality_status`
- **AND** 包含 `analysis_readiness`
- **AND** 包含 `parse_warnings`
- **AND** 包含 `parse_error`

#### Scenario: No normalized annotation available
- **WHEN** 文件未解析或无关联 NormalizedAnnotation
- **THEN** `normalized_annotation_id` MUST 为 null
- **AND** `quality_status` MUST 为 null

### Requirement: Repository resolves in a single LEFT OUTER JOIN

列表查询 SHALL 使用 `LEFT OUTER JOIN`，以 AnnotationFile 为主实体。未解析或 parse_failed 的文件 MUST 保留在列表中，对应关联字段为 null。

#### Scenario: No N+1 on list
- **WHEN** 系统返回标注文件列表
- **THEN** 系统 MUST NOT 对每条 AnnotationFile 逐条查询 NormalizedAnnotation

#### Scenario: Uploaded file without normalized annotation
- **WHEN** AnnotationFile 已上传但未解析
- **THEN** 列表项 MUST 返回 `normalized_annotation_id = null`
- **AND** `quality_status = null`
- **AND** 该行 MUST 仍然出现在列表中

#### Scenario: Parse failed file retained in list
- **WHEN** AnnotationFile.status = "parse_failed"
- **THEN** 列表项 MUST 仍然出现
- **AND** `parse_error` MUST 返回错误信息
