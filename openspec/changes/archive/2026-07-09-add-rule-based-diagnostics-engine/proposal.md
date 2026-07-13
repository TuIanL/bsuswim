## Why

Change #1–#3 打通了标注持久化、标准化标注层与 Kinovea 导入；Change #4 把标准化标注算成了结构化技术指标，并持久化到独立的 `annotation_metrics` 表（schema `swim-side-metrics.v1`）。但指标只是"发生了什么"，还不能告诉教练"这意味着什么、为什么重要、该怎么练"。

本 change 新增 **规则诊断引擎**，把侧面技术指标转成教练可读的结构化诊断（问题 / 严重程度 / 证据 / 原因 / 建议 / 优先级）。它是 `metrics → diagnostics → report` 闭环里缺失的中间层，也是路演材料里"从经验判断走向多视角数据诊断、专项反馈和长期追踪"目标的技术落地第一步。

### 与 Change #4 的真实衔接关系（关键修正）

原提案假设指标已经写在 `analysis_results.metrics`、诊断引擎从它读取。但 Change #4 明确"不修改 `analysis_results` 表结构"，指标落在 `annotation_metrics`（按 `normalized_annotation_id` 索引）。两条流水线在 Change #4 完成时仍是平行的、未接通的。因此本 change 必须显式补两层契约：

1. **`DiagnosticsMetricsAdapter`**：把 `annotation_metrics.summary` 的内部键（`body_angle_deg_avg`、`swolf.value`、`phase_metrics[]`、`front_reach_distance_cm_avg` 等）翻成**稳定逻辑键**（`body_angle_deg`、`swolf_value` 等），供规则 YAML 消费。未来 Task #4 内部键改名或 AI 姿态识别直接产出另一套 metrics，只改 adapter、规则不动。
2. **analysis_result 接线桥** `run_diagnostics_for_analysis_result`：按 `AnalysisResult → task → session → side SessionVideo → NormalizedAnnotation → AnnotationMetric(swim-side-metrics.v1)` 取数，跑引擎后写回 `analysis_results`。

### Scope 收窄（关键修正）

原提案暗示 12 条规则"全部可用"。实际上 Task #4 当前只产出约 7 条规则所需的核心键（`*_avg` 系、`swolf.value`、`kick_frequency_hz`）；`catch_area_score` / `propulsive_efficiency_score` / `efficiency_score` / `kick_interval_cv` / 分速度段划频划幅均未产出。因此：

- **v1 激活 7 条 active 规则**（R001/R002/R004/R006/R008/R009/R012），其余 5 条标记为 **dormant**；
- dormant 规则仍写进 YAML，但缺 `required_metrics` 时按 §14 优雅跳过，并写入 `diagnostics_meta.skipped_rule_ids`，使系统"为什么这次没判断某问题"完全可解释；
- 验收只要求 active 规则能命中，不再假装 12 条全活。

## What Changes

- 新增 `DiagnosticMetricsContext`：规则引擎的稳定输入契约（稳定逻辑键的 `metrics` + `manual_tags` + `quality_summary` + `phase_context`）。
- 新增 `DiagnosticsMetricsAdapter`（`backend/app/services/diagnostics/adapter.py`）：把 `annotation_metrics.metrics`（含 `summary`/`phase_metrics`/`cycles`）+ `NormalizedAnnotation.manual_tags` + `quality` 适配为 `DiagnosticMetricsContext`；记录 `missing_or_unsupported_metrics`。
- 新增规则引擎 `RuleBasedDiagnosticsEngine`（`backend/app/services/diagnostics/engine.py`）+ `evaluator.py`（仅支持结构化 `all` / `any` condition，不支持字符串表达式）+ `severity.py`（优先级/严重程度解析）+ `recommendation_mapper.py`。
- 新增规则注册表 `RuleRegistry`（`registry.py`）+ YAML 规则文件 `rules/side_freestyle_v1.yaml`：每条规则带 `status: active|dormant` 与 `required_metrics`；统一用结构化 `condition` 写 severity（不再支持字符串语法）。
- 新增 `diagnostics/models.py`：`DiagnosticItem` / `DiagnosticsSummary` / `DiagnosticsOutput` / `RuleEvaluationMeta` / `SkippedRuleMeta` / `DiagnosticMetricsContext`。
- 新增 `diagnostics/templates/`：`evidence_templates.py` / `reason_templates.py` / `suggestion_templates.py`（按 code 渲染中英文案，指标值带单位格式化，可选指标缺失时降级文案）。
- 新增接线桥 `run_diagnostics_for_analysis_result(db, analysis_result_id, rule_set, overwrite)`：解析 side `AnnotationMetric` → adapter → engine → 写回。
- 新增 alembic 迁移：给 `analysis_results` 加 `diagnostics` (JSONB, default `[]`) 与 `quality_summary` (JSONB, default `{}`)。Task #4 不改表结构是历史事实，本 change 的职责恰恰是把独立指标结果接回分析结果链路。
- 新增 API：`POST /api/analysis-results/{id}/diagnostics/run`、`GET /api/analysis-results/{id}/diagnostics`，返回 active diagnostics + skipped rule metadata + summary。
- 诊断结果写入 `analysis_results.diagnostics` 与 `analysis_results.raw_result["diagnostics_meta"]`（`rule_set` / `rule_version` / `engine_version` / `matched_rule_ids` / `skipped_rule_ids` / `generated_at`）。

## Capabilities

### New Capabilities
- `rule-based-diagnostics`：基于 `swim-side-metrics.v1` 指标 + 手动标签，通过可配置 YAML 规则产出结构化诊断（问题/严重程度/证据/原因/建议/优先级）并落 `analysis_results`，供 Change #6 `report_builder` 消费。

### Modified Capabilities
- `side-view-metrics`：明确其输出经 `DiagnosticsMetricsAdapter` 适配后供 diagnostics 消费（仅文档性补充，不改 metrics 计算逻辑）。
- `analysis-results-storage`：为 `analysis_results` 增加 `diagnostics` / `quality_summary` 列（新增 capability 或扩展现有 analysis 能力）。

## Impact

- 数据库：新增 `analysis_results.diagnostics` (JSONB) 与 `analysis_results.quality_summary` (JSONB) 两列（需迁移）。不修改 `annotation_metrics` / `normalized_annotations`。
- 规则 YAML 不绑定 `annotation_metrics.summary` 内部键，只认 `DiagnosticMetricsContext` 稳定逻辑键；内部键变动仅改 adapter。
- 报告层（Change #6）：本 change 产出 `analysis_results.diagnostics` 与 `raw_result.diagnostics_meta`，Change #6 的 `report_builder` 直接消费，不再负责"从哪拿指标"。
- 前端：新增两个 diagnostics 端点；不改变现有标注读写结构。
- 不涉及：机器学习诊断模型、LLM 生成诊断、多机位综合规则、前/俯视角专项诊断、体能/生理生化诊断、个体化长期趋势规则（均为非目标）。
