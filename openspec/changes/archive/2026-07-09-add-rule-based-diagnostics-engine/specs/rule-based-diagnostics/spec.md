# rule-based-diagnostics Specification

## Purpose
定义基于 `swim-side-metrics.v1` 指标 + 手动标签，通过可配置 YAML 规则产出结构化诊断（问题 / 严重程度 / 证据 / 原因 / 建议 / 优先级）的能力。诊断结果落 `analysis_results`，供 Change #6 `report_builder` 消费，形成"指标量化 → 问题诊断 → 训练建议 → 长期追踪"闭环的中间层。本能力不重算指标、不产出机器学习/LLM 诊断。

## ADDED Requirements

### Requirement: Diagnostics consume a stable metric context, not raw annotation_metrics keys
系统 SHALL 经 `DiagnosticsMetricsAdapter` 把 `annotation_metrics.metrics`（`*_avg` 系、`swolf.value`、`phase_metrics`、`manual_tags`、`quality`）适配为 `DiagnosticMetricsContext` 稳定逻辑键（`body_angle_deg`、`swolf_value` 等），规则引擎与 YAML 只消费稳定逻辑键。

#### Scenario: Raw side-view key is renamed in adapter
- **WHEN** Task #4 内部键 `body_angle_deg_avg` 被改名
- **THEN** 系统 MUST 仅在 `DiagnosticsMetricsAdapter` 调整映射，规则 YAML 与引擎代码 MUST NOT 随之改动

#### Scenario: swolf object is flattened
- **WHEN** `annotation_metrics.metrics.summary.swolf` 为 `{value: 88, ...}`
- **THEN** 系统 MUST 在 context 暴露标量 `swolf_value = 88`，规则 YAML MUST 只引用 `swolf_value`

### Requirement: Rules declare active or dormant status
系统 SHALL 在 YAML 中为每条规则标 `status: active | dormant` 与 `required_metrics`；dormant 规则或被判定缺 `required_metrics` 的 active 规则 MUST 被跳过而非报错，并记入 `diagnostics_meta.skipped_rule_ids`。

#### Scenario: Dormant rule is skipped with reason
- **WHEN** 规则 `status: dormant`（如 R007 缺 `catch_area_score`）
- **THEN** 系统 MUST 跳过该规则，并在 `skipped_rule_ids` 写入 `{id, reason: "dormant"}`

#### Scenario: Active rule missing required metric is skipped
- **WHEN** active 规则 R011 的 `required_metrics` 含 `stroke_rate_by_phase` 而 context 无此键
- **THEN** 系统 MUST 跳过该规则，并写入 `{id, reason: "missing_metric:stroke_rate_by_phase,stroke_length_by_phase"}`

### Requirement: Severity uses structured condition only
系统 SHALL 仅以结构化 `all` / `any` 条件（含 `metric` / `op` / `value`）表达 severity 与规则 condition，不得支持字符串表达式（如 `"swolf > 90 or efficiency_score < 60"`）。

#### Scenario: Partial evaluation when a metric is absent
- **WHEN** R012 的 `high` severity 含 `efficiency_score` 分支但该键缺失
- **THEN** 系统 MUST 仅用 `swolf_value` 分支判级，缺失分支记入 `partial_evaluation_warnings`，不得使整条规则失败

### Requirement: Diagnostics are written back to analysis_results via a bridge
系统 SHALL 提供 `run_diagnostics_for_analysis_result`，按 `AnalysisResult → task → session → side SessionVideo → NormalizedAnnotation → AnnotationMetric(swim-side-metrics.v1)` 解析 side 指标并写回 `analysis_results.diagnostics` 与 `raw_result.diagnostics_meta`。

#### Scenario: No side annotation metric found
- **WHEN** 该 analysis_result 对应 session 无 side 机位 `AnnotationMetric`
- **THEN** 系统 MUST 返回明确错误（404/422），不得静默产出空 diagnostics

#### Scenario: Diagnostics persisted for report consumption
- **WHEN** 引擎产出 7 条 active diagnostics
- **THEN** 系统 MUST 将 `DiagnosticItem[]` 写入 `analysis_results.diagnostics`，并将 `matched_rule_ids` / `skipped_rule_ids` / `rule_set` / `versions` / `generated_at` 写入 `raw_result.diagnostics_meta`

### Requirement: API exposes run and read endpoints
系统 SHALL 提供 `POST /api/analysis-results/{id}/diagnostics/run` 与 `GET /api/analysis-results/{id}/diagnostics`，返回 active diagnostics、`diagnostics_meta`（含 `skipped_rule_ids`）与 summary。

#### Scenario: Run returns active and skipped
- **WHEN** 以 Task #4 实际产物形态调用 run
- **THEN** 响应 MUST 含命中的 R001/R002/R004/R006/R008/R009/R012 与跳过 R003/R005/R007/R010/R011 的 `skipped_rule_ids`
