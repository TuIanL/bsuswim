## 1. Define diagnostics domain models

- [x] 1.1 新增 `backend/app/services/diagnostics/models.py`，定义 `DiagnosticItem`（code/title/category/severity/priority/evidence/reason/suggestion/metric_refs/manual_tag_refs/confidence/section_key/recommendation_tags/drill_refs）、`DiagnosticsSummary`、`DiagnosticsOutput`
- [x] 1.2 定义 `DiagnosticMetricsContext` 作为引擎稳定输入契约（稳定逻辑键的 `metrics` + `manual_tags` + `quality_summary` + `phase_context`）
- [x] 1.3 定义 `RuleEvaluationMeta` 与 `SkippedRuleMeta`（id / reason / partial_evaluation_warnings）

## 2. Add metrics adapter for swim-side-metrics.v1

- [x] 2.1 新增 `backend/app/services/diagnostics/adapter.py`：`DiagnosticsMetricsAdapter`，把 `annotation_metrics.metrics.summary` 的 `*_avg` 字段映射为稳定诊断逻辑键
- [x] 2.2 展平 `swolf.value` → `swolf_value`
- [x] 2.3 保留 `phase_metrics` 为 `phase_context`（供未来分速度段规则，不解析）
- [x] 2.4 透传 `NormalizedAnnotation.manual_tags` 与 `quality`（→ `quality_summary`）
- [x] 2.5 记录 `missing_or_unsupported_metrics`（如缺 `swolf.value` 时记 `swolf_value`）
- [x] 2.6 `manual_tags` 以 `NormalizedAnnotation.manual_tags` 为权威来源，仅当其缺失/为空时回退 `annotation_metrics.metrics.manual_tags`，统一输出 `context.manual_tags`
- [x] 2.7 `phase_metrics` 缺失/不足时，`skipped_rule_ids` 原因细分：`missing_metric:phase_context` / `insufficient_metric:phase_context.distance_markers` / `insufficient_metric:phase_context.speed_buckets`

## 3. Add YAML rule registry

- [x] 3.1 新增 `backend/app/services/diagnostics/rules/side_freestyle_v1.yaml` 与 `rule_schema.json`
- [x] 3.2 每条规则用**结构化 condition** 写 severity（仅 `all` / `any` + `metric`/`op`/`value`），不支持字符串表达式
- [x] 3.3 每条规则标 `status: active | dormant` 与 `required_metrics`
- [x] 3.4 12 条规则：7 条常活 active（R001/R002/R004/R006/R008/R009/R012）+ R003（active，required `phase_context`，缺失时跳过）+ R007/R010/R011（active，缺必需指标时跳过）+ R005（dormant，需人体尺度归一化）。跳过的 5 条与 §9 完全一致

## 4. Implement condition evaluator

- [x] 4.1 `backend/app/services/diagnostics/evaluator.py` 支持 `all` / `any`
- [x] 4.2 支持 metric 比较（`>=` `>` `<` `<=` `==` `!=`）
- [x] 4.3 点路径只在 adapter 内解析，规则里只认稳定逻辑键
- [x] 4.4 支持 `manual_tag` 匹配（与 metric 条件并列于 `any`）
- [x] 4.5 缺失 `required_metrics` 时整条规则优雅跳过，进 `skipped_rule_ids`

## 5. Implement severity and priority resolver

- [x] 5.1 `backend/app/services/diagnostics/severity.py` 从结构化 condition 解析 severity
- [x] 5.2 severity 分支引用的 metric 缺失 → 跳过该分支（记入 `partial_evaluation_warnings`），不使整条失败
- [x] 5.3 计算 `priority_score`（severity + category + evidence + manual_tag + multi_metric 权重）
- [x] 5.4 按 severity 与 priority_score 排序，输出 `priority = 1,2,3...`，后台保留 `priority_score`

## 6. Implement diagnostics text rendering

- [x] 6.1 `backend/app/services/diagnostics/templates/`：按 `code` 渲染 evidence / reason / suggestion
- [x] 6.2 指标值带单位格式化（° / cm / m / spm / hz）
- [x] 6.3 可选指标缺失时提供降级文案（不抛异常）

## 7. Implement deduplication and grouping

- [x] 7.1 定义 `diagnostic_groups`（如 `upper_limb_propulsion: primary=insufficient_high_elbow_catch`）
- [x] 7.2 合并上肢推进类重复问题：`keep_primary_attach_related_evidence`
- [x] 7.3 确保最终 diagnostics 是教练可读的、非机器罗列的结论
- [x] 7.4 R006（高肘抱水不足）与 R008（上肢推进效率不足）同时命中时，合并为单个上肢推进主问题，R008 证据作为 related evidence 附加；最终 diagnostics 不得出现两条并列的上肢推进问题

## 8. Connect diagnostics to real analysis results

- [x] 8.1 新增 `backend/app/services/diagnostics/bridge.py`：`run_diagnostics_for_analysis_result(db, analysis_result_id, rule_set, overwrite)`
- [x] 8.2 由 `AnalysisResult.task → session → side SessionVideo → NormalizedAnnotation → AnnotationMetric(swim-side-metrics.v1)` 解析 side 指标
- [x] 8.3 找不到 side `AnnotationMetric` 返回明确错误（422），不静默空跑
- [x] 8.4 写回 `analysis_results.diagnostics` 与 `analysis_results.raw_result["diagnostics_meta"]`（matched_rule_ids / skipped_rule_ids / rule_set / versions / generated_at）
- [x] 8.5 写 `raw_result["diagnostics_meta"]` 前先确保 `raw_result` 非 null（缺失则初始化为 `{}`），避免直接写嵌套键抛 `TypeError`

## 9. Add API endpoints

- [x] 9.1 `POST /api/analysis-results/{id}/diagnostics/run`（body: `rule_set`, `overwrite`）
- [x] 9.2 `GET /api/analysis-results/{id}/diagnostics`
- [x] 9.3 返回 active diagnostics + `diagnostics_meta`（含 `skipped_rule_ids`）+ summary
- [x] 9.4 明确定义错误码：`404`（analysis_result 不存在）/ `422`（存在但解析不到 side AnnotationMetric）/ `409`（已有 diagnostics 且 `overwrite=false`）

## 10. Migration & tests

- [x] 10.1 新增 alembic 迁移：`analysis_results` 加 `quality_summary`（JSON，default `{}`）；`diagnostics` 列已存在于迁移 0001，不重复加列（实现修正见 design §8）
- [x] 10.2 单测：adapter 正确映射 Task #4 `summary` 键；`swolf.value` → `swolf_value`
- [x] 10.3 单测：active 规则产出 diagnostics；dormant / 缺指标规则进 `skipped_rule_ids`
- [x] 10.4 单测：`run_diagnostics_for_analysis_result` 正确解析 side `AnnotationMetric` 并写回
- [x] 10.5 集成测试：§9 验收样例（真实 Task #4 键）命中 R001/R002/R004/R006/R008/R009/R012，跳过 R003/R005/R007/R010/R011
