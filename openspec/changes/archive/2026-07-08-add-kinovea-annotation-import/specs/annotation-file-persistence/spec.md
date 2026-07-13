# annotation-file-persistence Specification

## MODIFIED Requirements

### Requirement: Parse endpoint triggers status transition
`annotation_files` 的 status SHALL 在 parse 成功时流转为 `parsed`，parse 失败时流转为 `parse_failed` 并记录错误信息。Parse endpoint SHALL 使用已有的 `get_with_ownership_check` 进行权限校验，校验链路为 `annotation_file → session_video → training_session → coach`。

#### Scenario: Parse success sets status to parsed
- **WHEN** `POST /api/annotations/{annotation_file_id}/parse` 成功生成 normalized annotation
- **THEN** 系统 MUST 将 `annotation_files.status` 更新为 `parsed`

#### Scenario: Parse failure sets status to parse_failed
- **WHEN** parse 过程因数据格式错误、缺少必要字段或其他原因失败
- **THEN** 系统 MUST 将 `annotation_files.status` 更新为 `parse_failed`，并将错误描述写入 `annotation_files.parse_error`

#### Scenario: Unauthorized parse returns 403
- **WHEN** 调用方请求不属于当前用户可访问训练记录的 annotation_file
- **THEN** 系统 MUST 返回 404/403 错误，不得泄露其他用户的标注文件数据

## ADDED Requirements

### Requirement: Kinovea CSV parse replaces 501 skeleton
`parse_annotation_file` SHALL 对 `source=kinovea` 的标注文件调用 Kinovea parser，不再返回 501。

#### Scenario: CSV annotation file parsed successfully
- **WHEN** `annotation_file.file_type = "csv"` 且 `annotation_file.source = "kinovea"`
- **THEN** 系统 MUST 调用 Kinovea CSV parser 解析文件内容，生成 normalized annotation

#### Scenario: JSON annotation file path preserved
- **WHEN** `annotation_file.file_type = "json"` 且文件为有效的 Kinovea JSON
- **THEN** 系统 MUST 继续通过 JSON 路径解析，行为不变

### Requirement: Parse uses ownership-checked annotation file fetch
`parse_annotation_file` SHALL 使用 `annotation_repository.get_with_ownership_check` 获取 annotation_file，不再使用裸 `db.get`。

#### Scenario: Ownership check applied on parse
- **WHEN** 调用 `parse_annotation_file(db, annotation_file_id, current_user_id)`
- **THEN** 系统 MUST 先通过 `get_with_ownership_check` 校验权限，再执行解析
