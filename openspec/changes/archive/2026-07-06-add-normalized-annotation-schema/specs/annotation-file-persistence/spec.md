# annotation-file-persistence Specification

## ADDED Requirements

### Requirement: Parse endpoint triggers status transition
`annotation_files` 的 status SHALL 在 parse 成功时流转为 `parsed`，parse 失败时流转为 `parse_failed` 并记录错误信息。

#### Scenario: Parse success sets status to parsed
- **WHEN** `POST /api/annotations/{annotation_file_id}/parse` 成功生成 normalized annotation
- **THEN** 系统 MUST 将 `annotation_files.status` 更新为 `parsed`

#### Scenario: Parse failure sets status to parse_failed
- **WHEN** parse 过程因数据格式错误、缺少必要字段或其他原因失败
- **THEN** 系统 MUST 将 `annotation_files.status` 更新为 `parse_failed`，并将错误描述写入 `annotation_files.parse_error`

### Requirement: AnnotationSource enum reused by normalized annotations
`AnnotationSource` 枚举（kinovea / dartfish / manual_json / ai_pose / unknown）SHALL 被 `normalized_annotations.source` 复用，不另建新枚举。

#### Scenario: Normalized annotation references AnnotationSource
- **WHEN** 系统创建或校验 normalized annotation 的 source 字段
- **THEN** 系统 MUST 使用与 `annotation_files.source` 相同的 `AnnotationSource` Python Enum 和 PostgreSQL ENUM 类型
