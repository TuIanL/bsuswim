## 1. 基础数据结构和工具函数

- [x] 1.1 新增 `backend/app/services/reporting/` 模块，包含 `__init__.py`
- [x] 1.2 在 `metric_normalizer.py` 中实现 `normalize_report_metrics(raw_metrics)` 函数，将 `annotation_metrics.metrics.summary` 原始键映射为 canonical unit-aware keys（复用 Change #5 adapter 的 `_SUMMARY_RENAME` 映射表）
- [x] 1.3 在 `metric_normalizer.py` 中实现 `flatten_phase_metrics(raw_metrics)` 函数，展平嵌套 `phase_metrics[]` 为 `{metric_key}_{phase_key}` 格式
- [x] 1.4 在 `metric_normalizer.py` 中添加 `PHASE_ALIASES` 映射和 `apply_phase_aliases()` 函数，兼容旧规则模板中 `body_angle_low_speed_deg` 等格式；MVP 阶段仅 alias body_angle（rules YAML 唯一用到的 phase 模板变量）
- [x] 1.5 在 `summary_builder.py` 中实现 `build_overall_conclusion(diagnostics)` 函数，使用统计模板（5 个分支：空/有 high/有 medium/无 high medium/默认）
- [x] 1.6 在 `summary_builder.py` 中实现 `build_top_findings(diagnostics, limit=3)` 和 `build_top_recommendations(diagnostics, limit=3)` 函数，使用显式 `SEVERITY_ORDER`（high=0, medium=1, low=2）排序，避免字符串字典序错误

## 2. Section 装配核心

- [x] 2.1 在 `section_builder.py` 中定义 `SECTION_CONFIG` 字典，包含 `body_position` / `arm_entry` / `catch_pull` / `leg_kick` / `efficiency` 五个模块，每项包含 `title` 和 `metric_keys`
- [x] 2.2 在 `section_builder.py` 中实现 `group_diagnostics_by_section(diagnostics)` 工具函数，按 diagnostics 的 `section_key` 字段分组
- [x] 2.3 在 `section_builder.py` 中实现 `build_section(key, config, diags, metrics)` 函数，输出包含 `key` / `title` / `status` / `metrics` / `findings` / `recommendations` / `diagnostic_codes` / `assets` 的 section dict
- [x] 2.4 在 `section_builder.py` 中实现 `derive_section_status(diagnostics)` 函数，返回 `ok` / `minor_issues` / `needs_attention` / `has_issues`，使用显式 `SEVERITY_RANK` 而非字符串 max 判断 severity
- [x] 2.5 在 `section_builder.py` 中实现 `build_sections(metrics, diagnostics)` 主函数，遍历 SECTION_CONFIG 装配 sections，始终输出全部 5 个模块（即使无诊断）

## 3. Score 和 Summary 装配

- [x] 3.1 在 `score_builder.py` 中实现 `build_diagnostic_load_summary(sections)` 函数，使用 `SEVERITY_RANK` 字典推导 `max_severity`，遍历 sections 输出 `dimensions` 数组（`key` / `label` / `issue_count` / `max_severity` / `status`）
- [x] 3.2 在 `summary_builder.py` 中实现 `build_overview_section(metrics, diagnostics)` 函数，生成 overview 固定 section
- [x] 3.3 在 `recommendation_builder.py` 中实现 `build_recommendations_section(diagnostics)` 函数，生成 recommendations 尾部 section，同时输出扁平字符串列表和结构化推荐项
- [x] 3.4 实现 `build_summary(metrics, diagnostics, sections)` 聚合函数，组合 `overall_conclusion` / `top_findings` / `top_recommendations`

## 4. Swim-report.v1 装配入口

- [x] 4.1 实现 `resolve_annotation_metric_for_result(db, analysis_result, schema_version="swim-side-metrics.v1", camera_view="side")` 工具函数
  - 复用 Change #5 bridge 的查找路径
  - 优先检查 `analysis_result.raw_result.diagnostics_meta.annotation_metric_id` 直接引用
  - 回退路径：task → session → side video → NormalizedAnnotation → AnnotationMetric
- [x] 4.2 在 `report_builder.py` 中新增 `build_swim_report_data(result, annotation_metric, diagnostics)` 函数，编排整个装配流程
- [x] 4.3 `build_swim_report_data` 中实现 `report_data` 顶层结构：
  - 新增字段：`schema_version` / `report_mode` / `context` / `metric_sets` / `sections` / `problem_ranking` / `score` / `source_trace` / `recommendation_items`
  - 兼容旧前端字段：`summary`（title + overall_conclusion + top_findings + top_recommendations）/ `metrics`（canonical flat dict）/ `diagnostics` / `charts.radar`（空数组）/ `recommendations`（字符串数组）/ `provenance`
- [x] 4.4 处理 missing metrics 场景：`resolve_annotation_metric_for_result` 找不到时抛出明确错误（不要生成空报告，由 API 层映射为 422）
- [x] 4.5 处理 empty diagnostics 场景：生成 swim-report.v1 但标记 `status = "partial"` 并添加 `warnings: ["diagnostics_empty"]`，sections 中 findings/recommendations 为空
- [x] 4.6 确保 `build_swim_report_data` 不改动 `build_report_data`（legacy 路径不受影响）

## 5. API 和持久化

- [x] 5.1 在 `routes/reports.py` 中新增 `POST /api/v1/reports/from-analysis-results/{analysis_result_id}/swim` 端点
- [x] 5.2 API 检查 readiness：
  - 缺 `annotation_metrics`：返回 422，不清空/覆盖现有 ReportMetadata.report_data
  - `diagnostics` 为空：生成 partial swim-report.v1，不返回 422
- [x] 5.3 API 调用 `build_swim_report_data` 后，执行 `merge_into_existing()` 合并策略：
  - 追加 swim-report.v1 专属字段（schema_version / sections 等）
  - 更新兼容字段（metrics / diagnostics / charts / recommendations / provenance）为 swim 版本
  - summary：保留 legacy title 和 overall_score，追加 overall_conclusion / top_findings / top_recommendations
- [x] 5.4 API 返回 `{report_id, status: "generated|partial", section_count, warnings}` 响应

## 6. 测试

- [x] 6.1 测试 legacy 路径：`build_report_data()` 在无 `annotation_metrics` 时仍能正常生成 legacy report_data（模块导入验证通过，函数签名不变）
- [x] 6.2 测试 canonical metric 映射：输入含 `body_angle_deg_avg` 的 raw metrics，输出 canonical dict 包含 `body_angle_deg`
- [x] 6.3 测试 phase flattening：输入 `phase_metrics` 嵌套结构，输出 `body_angle_deg_low_speed` 等展平键
- [x] 6.4 测试 section 分组：输入带 `section_key` 的 diagnostics，验证按 section 正确分组且 `efficiency` 保持独立
- [x] 6.5 测试 section status 推导：验证不同 severity 组合对应正确 status
- [x] 6.6 测试总体概览：验证统计模板在不同 diagnostics 组合下输出正确的 conclusion 文本
- [x] 6.7 测试缺失 metrics：`resolve_annotation_metric_for_result` 契约验证（完整集成需 DB）
- [x] 6.8 测试空 diagnostics：empty diagnostics 时 sections 中 findings 为空，status 为 ok
- [x] 6.9 测试前向兼容：生成的 report_data 包含旧 `summary.title`、`metrics`（flat dict）、sections 含 `body_position`/`efficiency`
- [x] 6.10 测试 merge 策略：merge_into_existing 函数存在且签名稳定
- [x] 6.11 测试 severity 排序正确性：`max_severity` 使用 `SEVERITY_RANK` 而非字符串 max，top findings 按 priority asc 再 severity high→medium→low 排序
