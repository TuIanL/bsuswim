## Context

当前 `ReportView.vue` 用 115 行硬编码双栏布局消费扁平 `report_data`。Change #6 让后端产出了 `swim-report.v1` 结构（含 `sections`、`metric_sets`），但前端无法直接渲染。

约束：
- 不修改后端，不改路由 `/reports/:sessionId`
- 不替换 Element Plus，不引入新 UI 框架
- 不新增 DB 依赖或状态管理
- 不删除旧 demo 数据
- Change #6 后端 sections 不含 `type` 字段

## Goals / Non-Goals

**Goals:**
- 引入 `normalizeReportData(raw)` 适配层，统一 legacy 和 swim-report.v1
- `ReportSectionRenderer` 根据 section key/type 分配组件
- `ModuleSection` 按 `assets.length` + `charts.length` 自动选择子布局
- `ReportSummaryPanel` 保留 ECharts 雷达图
- Legacy diagnostics 归一化为 findings + recommendations
- 支持 `?demo_format=legacy|swim_v1` 切换
- 保持 loading / error / empty 状态和 provenance 显示

**Non-Goals:**
- 不改路由 `/reports/:sessionId` 为 `/reports/:reportId`
- 不做 PDF 导出
- 不替换 Element Plus
- 不引入新的状态管理（Vuex/Pinia for report state）
- 不删除旧 demo fixture
- 不要求后端新增 `section.type`

## Data Flow

```
ReportView.vue (entry)
  │
  ├── props: sessionId
  ├── route.query: ?demo_format=legacy|swim_v1
  │
  ▼
getReport(sessionId, { demoFormat })
  │
  ▼
normalizeReportData(raw)
  │  detect swim-report.v1 by schema_version || sections[]
  │  normalize legacy report into view model
  │  preserve charts.radar, provenance
  │
  ▼
NormalizedReportViewModel
  ├── title: string
  ├── summary: { overallScore?, radar?, findings? }
  ├── sections: NormalizedSection[]
  └── provenance: {...}
      │
      ▼
  ReportSectionRenderer
    ├── ModuleSection      ← 按 resolveModuleLayout() 选子布局
    ├── GenericSection     ← 兜底，Phase 7a 中 also handles overview/trend/recommendation
    └── （Phase 7b 补充）    ← 按需添加 Overview/Trend/Recommendation 专用组件
```

## Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | 保留 `/reports/:sessionId` 路由 | 不改 API 契约，现有页面跳转不中断 |
| D2 | 用 `resolveSectionKind()` 三层回退 | section.type → section.key → shape inference → generic，兼容后当前缺少 type |
| D3 | ModuleSection 按 `assets.length` + `charts.length` 选布局 | 不依赖后端 layout 字段，身体位置(3图)/抱水(2图+图)/效率(纯图)自动适配 |
| D4 | Legacy diagnostics 拆为 findings + recommendations | 保留 evidence 和 suggestion 的层级，不丢字段 |
| D5 | Radar chart 保留在 SummaryPanel | 它是综合能力画像，不属于任何技术 section |
| D6 | Element Plus 保留外层，report 内容用自定义 CSS | 外层结构（按钮/标签/状态/描述）继续使用 EP，报告模块用独立 class 避免笨重 |
| D7 | `?demo_format=legacy|swim_v1` 查询参数切换 | 不用全局设置、不用 localStorage、截图和开发都方便 |
| D8 | 一个 change 两阶段实现 | 阶段 A 做 renderer 内核 + 适配层，阶段 B 做视觉完善 + demo fixture |

## ModuleSection 布局规则

```
assets >= 3 && charts = 0  → frame_grid_3     (body_position: 3 speed stages)
assets = 2  && charts = 0  → frame_grid_2     (arm_entry: 2 frames)
assets > 0  && charts > 0  → mixed_media       (catch_pull: frames + charts)
charts >= 1 && assets = 0  → chart_grid        (efficiency: speed/rate/length trends)
其他                        → compact            (minimal or text-only sections)
```

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Phase 7a 时部分 section 类型无专用组件，用 GenericSection 兜底导致视觉平淡 | 在设计阶段就接受——GenericSection 职责就是兜底，等 7b 补专用组件 |
| Legacy report adapter 的信息损失（旧 diagnostics 没有 section_key） | 全部归入一个 `legacy_diagnostics` section，多 sections 不可能 |
| Radar chart 在新 swim-report.v1 中为空，用户看不到雷达图 | swim-report.v1 的 radar 数据等 score/metric_sets 就绪后再补，不阻塞 Task 7 |
| 新旧 demo 切换依赖 URL 参数，前端开发时需要手动加 `?demo_format=swim_v1` | 可以加一个简单的 dev panel 或 cookie，但 MVP 用 query param 已够 |
