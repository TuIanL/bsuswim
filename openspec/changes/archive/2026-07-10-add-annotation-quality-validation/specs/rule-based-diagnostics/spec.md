# rule-based-diagnostics Specification (Delta)

## ADDED Requirements

### Requirement: Diagnostic context splits quality into three namespaces
`DiagnosticMetricsContext` SHALL 包含 `annotation_quality`（标注输入质量）、`metric_quality`（指标计算质量）和 `quality_decision`（聚合可用性决策）三个独立命名空间，代替原有单一 `quality_summary`。

#### Scenario: Quality decision drives rule skipping
- **WHEN** `quality_decision.module_availability.catch_pull = "blocked"`
- **THEN** 引擎 MUST 跳过所有 `section_key: "catch_pull"` 的规则，计入 `skipped_rule_ids`

#### Scenario: Metric quality drives confidence
- **WHEN** `elbow_angle_deg_avg` 的 `metric_availability = "low_confidence"`
- **THEN** 对应诊断的 `confidence` 字段 MUST 设置为 `low`

#### Scenario: Backward compatible quality_summary retained
- **WHEN** 读取旧 `quality_summary`（非 analysis-quality.v1 结构）
- **THEN** 系统 MUST 将其映射为 `metric_quality`，`annotation_quality` 和 `quality_decision` 由兼容 adapter 填充默认值

### Requirement: Diagnostics bridge validates quality before run
`run_diagnostics_for_analysis_result` SHALL 检查 `NormalizedAnnotation.quality.status`。如果为 `invalid` 且未强制运行，则抛出 `AnnotationQualityBlockedError`。

#### Scenario: Blocked by invalid quality
- **WHEN** `AnnotationQualityReport.status = "invalid"` 且 `force=False`
- **THEN** bridge MUST 抛出 `AnnotationQualityBlockedError`

#### Scenario: Force bypasses quality check
- **WHEN** `force=True` 且 `quality.status = "invalid"`
- **THEN** bridge MUST 仍运行 diagnostics，但 `DiagnosticMetricsContext.quality_decision` 标记所有模块为 `blocked`
