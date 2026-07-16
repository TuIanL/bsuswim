## ADDED Requirements

### Requirement: Parse response quality uses v2 AnnotationQualityReport

`ParseResponse.quality` SHALL 使用 `AnnotationQualityReport`（已有的 v2 Pydantic model），不应强制转换为 legacy `AnnotationQuality` 类型。`quality` 字段类型 SHALL 为 `AnnotationQualityReport`，使用 `model_validate()` 装配，保留强类型校验。

#### Scenario: CVAT parse returns v2 quality

- **WHEN** API 请求 `POST /api/annotations/{annotation_file_id}/parse` 且 `source = "cvat"`
- **THEN** `response.quality.status` MUST 为 `valid`/`warning`/`invalid` 之一
- **THEN** `response.quality` MUST NOT 包含 `level` 字段
- **THEN** `response.analysis_readiness` MUST 与 `response.quality.status` 语义一致，不自相矛盾

### Requirement: Re-validate uses correct profile

`POST /api/normalized-annotations/{id}/validate` 端点 SHALL 根据 `NormalizedAnnotation.source` 选择对应的 quality profile，而不是硬编码为 `side_technical_v1`。

#### Scenario: CVAT annotation uses CVAT profile

- **WHEN** `ann.source == "cvat"`
- **THEN** validate 端点 MUST 使用 `side_technical_v1_cvat` profile

#### Scenario: Kinovea annotation uses default profile

- **WHEN** `ann.source == "kinovea"`
- **THEN** validate 端点 MUST 使用 `side_technical_v1` profile

### Requirement: Profile resolver is shared

parse 和 validate 端点 SHALL 共用同一个 profile 解析函数，确保两个阶段使用相同的 profile。

#### Scenario: Profile resolver accepts source (not ORM object)

- **WHEN** parse 端点（NormalizedAnnotation 创建前）需要确定 quality profile
- **THEN** resolver MUST 接受 `source` 值（`str | AnnotationSource`），而非 ORM 对象

#### Scenario: Profile resolver called from both endpoints

- **WHEN** parse 端点或 validate 端点需要确定 quality profile
- **THEN** 两者 MUST 调用同一 `resolve_quality_profile_id(source)` 函数
