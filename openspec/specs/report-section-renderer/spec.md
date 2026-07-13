# report-section-renderer Specification

## Purpose
TBD - created by change refactor-report-frontend-section-renderer. Update Purpose after archive.

## Requirements

### Requirement: ReportView normalizes diverse report formats

系统 SHALL 通过 `normalizeReportData(raw)` 适配层统一消费 legacy report_data 和 swim-report.v1 两种后端格式。

#### Scenario: Legacy report is normalized
- **WHEN** 后端返回不包含 `schema_version` 或 `sections` 的扁平 report_data
- **THEN** 系统 MUST 将其转换为统一 `NormalizedReportViewModel`，legacy diagnostics 拆为 findings 和 recommendations，`charts.radar` 保留到 summary 层

#### Scenario: swim-report.v1 is normalized
- **WHEN** 后端返回 `schema_version === "swim-report.v1"` 且包含 `sections` 数组
- **THEN** 系统 MUST 直接使用其 sections，不执行额外转换

### Requirement: Section renderer resolves by key fallback

系统 SHALL 在没有 `section.type` 时，通过 `section.key` 映射或数据形态推断确定渲染组件。

#### Scenario: Section type is missing
- **WHEN** section 数据有 `key` 但无 `type`
- **THEN** 系统 MUST 通过 `SECTION_KEY_KIND_MAP`（如 `body_position` → `module`）确定渲染方式
- **WHEN** section key 也不在映射表中
- **THEN** 系统 MUST 通过数据形态推断（有 charts → trend，有 assets → module，仅 recommendations → recommendation）
- **WHEN** 全部推断失败
- **THEN** 系统 MUST 使用 `GenericSection` 组件渲染，不得崩溃

### Requirement: ModuleSection auto-selects layout

系统 SHALL 使用单一 `ModuleSection` 组件，根据 `assets.length` 和 `charts.length` 自动切换子布局。

#### Scenario: Three-asset section uses triple frame grid
- **WHEN** `section.assets.length >= 3` 且 `section.charts.length === 0`
- **THEN** `ModuleSection` MUST 使用三列网格布局 (`frame_grid_3`)

#### Scenario: Mixed assets and charts uses mixed media layout
- **WHEN** `section.assets.length > 0` 且 `section.charts.length > 0`
- **THEN** `ModuleSection` MUST 使用左右混合布局 (`mixed_media`)

#### Scenario: Charts-only section uses chart grid
- **WHEN** `section.charts.length >= 1` 且 `section.assets.length === 0`
- **THEN** `ModuleSection` MUST 使用图表网格布局 (`chart_grid`)

### Requirement: Legacy radar chart is preserved

系统 SHALL 在 `ReportSummaryPanel` 中保留 ECharts 雷达图渲染能力。

#### Scenario: Radar data exists in legacy report
- **WHEN** 标准化的 viewModel 中包含 `summary.radar` 数据
- **THEN** `ReportSummaryPanel` MUST 使用 ECharts 渲染雷达图

#### Scenario: No radar data
- **WHEN** swim-report.v1 不包含 radar 数据
- **THEN** `ReportSummaryPanel` MUST 不渲染雷达图区域，不报错

### Requirement: Legacy diagnostics are split into findings and recommendations

系统 SHALL 将旧格式的 diagnostics 数组拆分为 `findings`（承载 evidence）和 `recommendations`（承载 suggestion）。

#### Scenario: Diagnostic with evidence and suggestion
- **WHEN** 旧 diagnostic 同时包含 `evidence` 和 `suggestion`
- **THEN** 系统 MUST 生成两条：一条 finding（title + evidence + severity），一条 recommendation（suggestion）
- **WHEN** 旧 diagnostic 只有 evidence 没有 suggestion
- **THEN** 系统 MUST 仅生成 finding，不生成空 recommendation

### Requirement: Demo fixtures support dual format

系统 SHALL 同时保留 legacy demo report 和 swim-report.v1 demo fixture，通过 `?demo_format=legacy|swim_v1` 切换。

#### Scenario: Legacy demo format
- **WHEN** URL 包含 `?demo_format=legacy` 或未指定
- **THEN** 系统 MUST 返回旧格式 demo report

#### Scenario: swim-report.v1 demo format
- **WHEN** URL 包含 `?demo_format=swim_v1`
- **THEN** 系统 MUST 返回 swim-report.v1 格式的 demo report，包含 sections
