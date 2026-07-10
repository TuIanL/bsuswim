# annotation-file-persistence Specification (Delta)

## MODIFIED Requirements

### Requirement: Parse response includes quality status and analysis_readiness
`ParseResponse` SHALL 在 `quality` 中包含 `status`（valid/warning/invalid），并新增 `analysis_readiness` 对象（含 `can_submit`、`requires_acknowledgement`、`blocking_issue_count`、`affected_modules`），替代简单布尔值 `can_analyze`。

#### Scenario: Parse response quality has analysis_readiness
- **WHEN** parse 成功
- **THEN** 响应 MUST 包含 `quality.status` 和 `analysis_readiness`（含 can_submit、requires_acknowledgement、blocking_issue_count、affected_modules）

#### Scenario: Valid annotation readiness
- **WHEN** quality.status = `valid`
- **THEN** `analysis_readiness.can_submit` MUST 为 `true`，`requires_acknowledgement` MUST 为 `false`

#### Scenario: Warning annotation readiness
- **WHEN** quality.status = `warning`
- **THEN** `analysis_readiness.can_submit` MUST 为 `true`，`requires_acknowledgement` MUST 为 `true`，`affected_modules` 列出降级模块

#### Scenario: Invalid annotation readiness
- **WHEN** quality.status = `invalid`
- **THEN** `analysis_readiness.can_submit` MUST 为 `false`，`requires_acknowledgement` MUST 为 `false`

#### Scenario: Parse succeed annotation invalid
- **WHEN** 文件成功解析为 NormalizedAnnotation 但 quality = invalid
- **THEN** `annotation_file.status` MUST 为 `parsed`（非 `parse_failed`），`ParseResponse.quality.status` = `"invalid"`

## ADDED Requirements

### Requirement: Parser warnings delegate semantic checks to validator
parser SHALL 不再维护 `RECOMMENDED_EVENTS` 等游泳专项语义 warning。语义检查职责移交 `AnnotationQualityValidator` profile。

#### Scenario: Missing catch_start warning from validator not parser
- **WHEN** parse 时发现缺少 `catch_start` 事件
- **THEN** parser MUST 不生成该 warning；该 warning 由 `AnnotationQualityValidator` 在后续验证中产生
