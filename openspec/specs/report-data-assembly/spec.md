# report-data-assembly Specification

## Purpose
TBD - created by change assemble-swim-report-data. Update Purpose after archive.

## Requirements

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

## ADDED Requirements

### Requirement: Five-page kinematics report profile is supported

The system SHALL support report profile `side_2d_kinematics_5page_v1` in addition
to the existing `side_technical` profile.

The `side_2d_kinematics_5page_v1` profile SHALL assemble exactly five pages from
`AnnotationMetric(swim-side-kinematics.v1)`, the current
`KinematicArtifactSet`, and the current `KinematicReviewFindingSet`, without
depending on `AnalysisResult.diagnostics`.

#### Scenario: Five-page profile uses its own page types

- **WHEN** report profile `side_2d_kinematics_5page_v1` is assembled
- **THEN** sections SHALL use page types
  `overview` / `body_posture_control` / `upper_limb_kinematics` /
  `lower_limb_kinematics` / `review_and_retest`
- **AND** the legacy `side_technical` section keys SHALL NOT be used

### Requirement: Report-page module keys are profile-specific

For `side_2d_kinematics_5page_v1`, `section.module_key` SHALL identify the
report-page aggregation module and SHALL NOT be interpreted as an artifact
`module_key` or a legacy `side_technical` section key.

#### Scenario: Page module key differs from artifact module key

- **WHEN** page 2 of the five-page profile is assembled
- **THEN** `section.module_key` SHALL be `body_posture_head_trunk`
- **AND** each asset within the section SHALL retain its artifact `module_key`
- **AND** `section.source_module_keys` SHALL list the fact source modules

### Requirement: Report assembly status is distinct from upstream status

For `side_2d_kinematics_5page_v1`, the top-level report SHALL expose
`assembly_status` (`ready` / `partial`), separate from the upstream
`artifact_set.status` and `finding_set.status` namespaces.

#### Scenario: Legacy path is unchanged

- **WHEN** the legacy `build_swim_report_data()` path is used
- **THEN** its existing behavior and `status` semantics SHALL remain unchanged
- **AND** the new `assembly_status` field applies only to the five-page profile

### Requirement: Report sections include availability status

`ReportData.sections[]` SHALL include `availability`
(ready/degraded/blocked), `data_confidence` (high/medium/low/null) and
`quality_notes` (string array) fields, representing data availability rather than
technical diagnostic status.

This requirement applies to the legacy `side_technical` profile and its
`build_swim_report_data()` path. The new `side_2d_kinematics_5page_v1` profile
uses `section.status` (ready/partial/unavailable) and `assembly_status` instead,
as defined in the `five-page-kinematics-report` capability. The two profiles
remain independent.

#### Scenario: Blocked section with no findings

- **WHEN** `catch_pull` module availability = `blocked`
- **THEN** the section MUST contain `availability: "blocked"`, `metrics: []`,
  `findings: []`, `quality_notes` explaining the block reason

#### Scenario: Degraded section reports limited data

- **WHEN** `catch_pull` module availability = `degraded` and diagnostics have findings
- **THEN** `status` (technical diagnostic) MAY still be `has_issues`,
  `availability` stays `degraded`, `quality_notes` explains missing data

### Requirement: ReportData.quality carries aggregated quality

`ReportData.quality` SHALL 包含 `AnalysisResult.quality_summary` 的报告呈现版本（annotation quality summary、metrics quality summary、decision）。

#### Scenario: Quality section in report data

- **WHEN** `build_swim_report_data` 消费 `AnalysisResult.quality_summary`
- **THEN** `report_data.quality` MUST 包含 `annotation`、`metrics`、`decision` 三个命名空间

### Requirement: PDF omits blocked sections

PDF 渲染 SHALL 根据 `section.availability` 决定是否包含该模块。`blocked` 模块默认省略并在数据质量说明中列出；`degraded` 模块正常渲染但附带质量说明。

#### Scenario: Blocked section omitted from PDF

- **WHEN** section.availability = `blocked`
- **THEN** PDF 渲染器 MUST 跳过该 section，并在报告的数据质量说明中提及

#### Scenario: Degraded section included with note

- **WHEN** section.availability = `degraded`
- **THEN** PDF 渲染器 MUST 包含该 section，并在 section 内展示 `quality_notes`
