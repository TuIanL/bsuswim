## Why

当前前端报告页 `ReportView.vue` 使用硬编码的双栏布局（左侧指标+雷达图、右侧诊断+来源），直接消费后端返回的扁平 `report_data`。Change #6 新增了 `swim-report.v1` 结构化报告数据（带 `sections` 数组和 `metric_sets`），但前端目前无法渲染这一新格式。如果不做改造，前后端之间的报告数据链路会断裂——后端产出了丰富结构，前端却只能展示扁平版本。

## What Changes

- 在现有 `ReportView.vue` 中引入兼容型 section renderer，不替换当前页面入口
- 新增 `normalizeReportData(raw)` 适配层，统一消费 legacy 报告和 `swim-report.v1`
- 新增 `ReportSectionRenderer` 组件，根据 section key / type 渲染对应模块
- 新增 `ModuleSection` 组件，按 `assets.length` 和 `charts.length` 自动选择子布局（三列图/两列图/混合/图表/紧凑）
- 新增 `ReportSummaryPanel` 保留 ECharts 雷达图渲染能力
- 新增 `?demo_format=legacy|swim_v1` 查询参数，支持两种 demo 报告切换
- 不修改后端，不改路由，不替换 Element Plus，不做 PDF 导出
- **BREAKING**: `ReportView.vue` 主体从 `grid-two` 双栏布局改为从上到下的 section flow

## Capabilities

### New Capabilities
- `report-section-renderer`: 前端 section-based 报告渲染能力，将后端返回的 swim-report.v1 sections 或 legacy report_data 适配为统一视图，按 section key 分配渲染组件，支持 ModuleSection 内部密度自适应布局

### Modified Capabilities
- `swim-interactive-performance-report`: 报告渲染需求补充——前端报告页 SHALL 支持后端 swim-report.v1 格式，在无 `section.type` 字段时按 section.key 映射渲染

## Impact

- `frontend-vue/src/views/ReportView.vue`: 主体渲染（~35行）替换为 section flow
- `frontend-vue/src/types.ts`: 新增 `ReportSection`, `ReportMetric`, `ReportFinding` 等视图模型类型
- `frontend-vue/src/utils/`: 新增 `reportAdapter.ts`（normalizeReportData）、`reportSections.ts`（resolveSectionKind / resolveModuleLayout）
- `frontend-vue/src/components/report/`: 新增 ReportSectionRenderer, ReportSummaryPanel, ModuleSection, GenericSection, MetricCard, FindingList, RecommendationList, ReportChart
- `frontend-vue/src/services/api.ts`: 增加 `?demo_format` 查询参数支持
- `frontend-vue/src/services/demoData.ts`: 新增 swim-report.v1 demo fixture
