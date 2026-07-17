## ADDED Requirements

### Requirement: Parse warnings persisted in annotation_metadata

`parse_annotation_file()` SHALL 将 warnings 持久化到 `NormalizedAnnotation.annotation_metadata.parse.warnings`。

#### Scenario: Warnings written on successful parse
- **WHEN** parse 成功且产生 warnings
- **THEN** `annotation_metadata.parse.warnings` MUST 包含 warning 列表
- **AND** `annotation_metadata.parse.parsed_at` MUST 为解析时间戳

#### Scenario: Warnings overwritten on re-parse
- **WHEN** 同一文件重新解析
- **THEN** `annotation_metadata.parse.warnings` MUST 被新 warnings 覆盖
- **AND** MUST NOT 追加到旧 warnings

#### Scenario: Parse failure does not overwrite metadata
- **WHEN** parse 失败
- **THEN** 系统 MUST NOT 修改 `annotation_metadata.parse`
