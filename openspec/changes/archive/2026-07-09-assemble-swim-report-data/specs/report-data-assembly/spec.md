## ADDED Requirements

### Requirement: ReportData uses swim-report.v1 schema

系统 SHALL 将 `annotation_metrics.metrics` 事实指标与 `analysis_results.diagnostics` 诊断结果装配为 `swim-report.v1` 结构的 ReportData，写入 `ReportMetadata.report_data`。

#### Scenario: ReportData includes schema version
- **WHEN** 系统生成 swim-report.v1
- **THEN** `report_data` MUST 包含 `schema_version: "swim-report.v1"`、`report_mode: "side_technical"`、`context`（关联的 analysis_result_id / annotation_metric_id / session_id / task_id）

#### Scenario: ReportData sections are driven by diagnostic section_key
- **WHEN** 系统按 section_key 分组 diagnostics
- **THEN** 系统 MUST 使用 rules YAML 的 section_key（`body_position` / `arm_entry` / `catch_pull` / `leg_kick` / `efficiency`）作为报告 section key，不得引入第二套命名

#### Scenario: Efficiency section is independent
- **WHEN** diagnostics 包含 `efficiency` 分类的规则
- **THEN** 系统 MUST 生成独立的 `efficiency` section，不得合并入 `catch_pull`

### Requirement: Report metrics use canonical keys

系统 SHALL 将 `annotation_metrics.metrics` 原始键（如 `body_angle_deg_avg`）标准化为带单位的 canonical 键（如 `body_angle_deg`），并保留原始数据。

#### Scenario: Metrics include canonical and raw views
- **WHEN** 原始 metrics 包含 `body_angle_deg_avg: 12.4`
- **THEN** `report_data.metrics` MUST 包含 `body_angle_deg: 12.4`（canonical），同时 `metric_sets.raw.body_angle_deg_avg: 12.4` 保留原始值

#### Scenario: Phase metrics are flattened
- **WHEN** `annotation_metrics.metrics.phase_metrics` 包含 `{phase_key: "low_speed", metrics: {body_angle_deg: 14}}`
- **THEN** 系统 MUST 展平为 `report_data.metric_sets.phase.body_angle_deg_low_speed: 14`，格式为 `{metric_key}_{phase_key}`

#### Scenario: Metric evaluation is nullable
- **WHEN** section 包含 ReportMetric
- **THEN** `evaluation` 字段 MAY 为 `null`，本 capability 不做 metric-level 评价

### Requirement: Report data sources follow annotation_metrics path

系统 SHALL 从 `annotation_metrics` 表读取事实指标用于 swim-report.v1 生成，不得回退到 `AnalysisResult.metrics`。

#### Scenario: Annotation metric not found
- **WHEN** build_swim_report_data 调用时找不到关联的 `AnnotationMetric(schema_version="swim-side-metrics.v1")`
- **THEN** 系统 MUST 返回明确的 partial/error 状态（`status: "missing_metrics"`），不得静默生成空报告

#### Scenario: Diagnostics not found
- **WHEN** `analysis_result.diagnostics` 为空
- **THEN** 系统 MAY 仍生成报告，但 `sections` 中各模块的 findings/recommendations 为空，`score.dimensions` 标记为 `status: "ok"`

### Requirement: Diagnostic load summary replaces numeric scoring

系统 SHALL 基于 section 内诊断结果生成问题负荷摘要，不伪造维度评分。

#### Scenario: Section status is derived from diagnostics
- **WHEN** section 的 diagnostics 包含 high severity 问题
- **THEN** `score.dimensions[].status` MUST 为 `"has_issues"`
- **WHEN** section 的 diagnostics 仅有 low severity 问题且数量 < 3
- **THEN** `score.dimensions[].status` MUST 为 `"minor_issues"`
- **WHEN** section 无任何 diagnostics
- **THEN** `score.dimensions[].status` MUST 为 `"ok"`

### Requirement: Summary uses deterministic template

系统 SHALL 使用统计模板生成 `overall_conclusion`，不做自由文本生成。

#### Scenario: Overall conclusion is count-based
- **WHEN** diagnostics 包含 high severity 问题
- **THEN** `summary.overall_conclusion` MUST 模板化为 `"本次分析发现 {total} 个主要技术问题，其中高严重度问题 {high_count} 个，建议优先处理。"`

#### Scenario: Top findings come from diagnostics
- **WHEN** diagnostics 已按优先级排序
- **THEN** `summary.top_findings` MUST 包含前 3 条诊断的 title，`summary.top_recommendations` 包含对应的 suggestion
