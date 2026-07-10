# report-data-assembly Specification (Delta)

## ADDED Requirements

### Requirement: Report sections include availability status
`ReportData.sections[]` SHALL 新增 `availability`（ready/degraded/blocked）、`data_confidence`（high/medium/low/null）和 `quality_notes`（string 数组）字段，表示数据可用性而非技术诊断状态。

#### Scenario: Blocked section with no findings
- **WHEN** `catch_pull` 模块 availability = `blocked`
- **THEN** 该 section MUST 包含 `availability: "blocked"`，`metrics: []`、`findings: []`，`quality_notes` 说明阻断原因

#### Scenario: Degraded section reports limited data
- **WHEN** `catch_pull` 模块 availability = `degraded` 且诊断有发现
- **THEN** `status`（技术诊断）仍可设为 `has_issues`，`availability` 保持 `degraded`，`quality_notes` 说明哪些数据缺失

#### Scenario: Section without issues is not blocked
- **WHEN** 模块 availability = `degraded` 但无诊断命中
- **THEN** `status` 仍为 `ok`，`availability` 为 `degraded`，`quality_notes` 说明数据限制

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
