## Why

当前报告数据装配 `build_report_data(task, result)` 直接在 `save_analysis_result()` 同步执行，依赖 `AnalysisResult.metrics`（模型服务原始输出）。但过去两个 Change 已明确将事实指标的权威来源定为独立的 `annotation_metrics` 表（Change #4），诊断结果也基于此（Change #5）。现有报告链路走了一条捷径，没有走通 `normalized_annotations → annotation_metrics → diagnostics → ReportData` 的完整链路，导致 swim-report.v1 格式的报告无法正确读取 annotation_metrics 侧的指标和速度阶段数据。

## What Changes

- 引入双轨报告生成：保留现有 `save_analysis_result()` 内 legacy 报告，新增 `swim-report.v1` 装配路径
- 新增 `swim-report.v1` 报告数据格式：包含 `sections` 模块化结构、canonical metrics、phase metrics、diagnostic-driven findings
- `swim-report.v1` 的 metrics 来源改为 `annotation_metrics.metrics`，不再依赖 `AnalysisResult.metrics`
- 新增显式 swim-report 生成 API，不在 `save_analysis_result()` 同步生成
- 数据结构向后兼容：保留旧前端消费字段（`summary.title`、`metrics`、`diagnostics`、`charts.radar`），新增 sections 等字段
- 不迁移前端到 section renderer、不做 PDF 导出、不做 visual_assets 存储

## Capabilities

### New Capabilities
- `report-data-assembly`: 将 `annotation_metrics` 事实指标与 `analysis_results.diagnostics` 诊断结果装配为 `swim-report.v1` 结构的 ReportData，包含 canonical metric 标准化、phase metrics 展平、diagnostics section 分组、summary 模板生成

### Modified Capabilities
- `swim-interactive-performance-report`: 更新"后端生成的报告数据"需求——承认双轨并存：legacy 报告仍由模型服务输出生成，swim-report.v1 报告由 annotation_metrics + diagnostics 生成，且报告生成时机延后（不绑定在 save_analysis_result 内）

## Impact

- `backend/app/services/report_builder.py`: 新增 `build_swim_report_data()` 函数，保留 `build_report_data()` 不动
- `backend/app/services/reporting/`: 新增 `schemas.py`（ReportData Pydantic 结构）、`metric_normalizer.py`（canonical key 映射 + phase flatten）、`section_builder.py`（section 装配）
- `backend/app/api/routes/reports.py`: 新增显式 swim-report 生成/刷新 API
- `backend/app/models/report.py`: 不新增列，ReportMetadata 结构不变
- `ReportMetadata.report_data`: 内部结构扩展为 swim-report.v1（叠加在旧字段之上）
- 现有 frontend `ReportView.vue`: 不受影响（旧字段保留）
