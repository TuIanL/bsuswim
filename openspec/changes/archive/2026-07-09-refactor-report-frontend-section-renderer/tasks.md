## Phase 7a: Renderer foundation

- [x] 7.1 Add frontend report view model types.
  - Create `NormalizedReportViewModel`, `ReportSection`, `ReportMetric`, `ReportFinding`, `ReportRecommendation`, `ReportAsset`, `ReportChart` interfaces.
  - Make `section.type` optional.
  - Add to `frontend-vue/src/types/report.ts`.

- [x] 7.2 Add `normalizeReportData(raw)` adapter.
  - Detect `swim-report.v1` by `schema_version` or `sections` presence.
  - Normalize legacy report into `NormalizedReportViewModel`.
  - Preserve `charts.radar` in `summary.radar`.
  - Preserve `provenance` at top level.

- [x] 7.3 Add legacy diagnostics normalization.
  - Map each legacy diagnostic `title + evidence + severity` into a finding with explicit `evidence` field.
  - Map `suggestion` into a recommendation with explicit `content` field.
  - Preserve source diagnostic as `source_diagnostic` for full traceability.
  - `ReportFinding`: `{ key, title?, evidence?, content?, severity?, source_diagnostic? }`
  - `ReportRecommendation`: `{ key, title?, content, priority?, source_diagnostic? }`

- [x] 7.4 Add `resolveSectionKind(section)` helper with correct priority.
  - Prefer `section.type` if present.
  - Match known technical keys (`body_position`, `arm_entry`, `catch_pull`, `leg_kick`) → `module` before shape inference.
  - Match overview / recommendation keys → `overview` / `recommendation`.
  - Match `efficiency` / trend keys → `trend`.
  - Shape inference: return `trend` only if section has charts AND no assets/findings/metrics.
  - Shape inference: return `module` if section has assets, findings, or metrics.
  - Return `generic` as final fallback.

- [x] 7.5 Add `resolveModuleLayout(section)` helper.
  - `assets >= 3 && charts = 0` → `frame_grid_3`.
  - `assets = 2 && charts = 0` → `frame_grid_2`.
  - `assets > 0 && charts > 0` → `mixed_media`.
  - `charts >= 1 && assets = 0` → `chart_grid`.
  - Otherwise → `compact`.

- [x] 7.6 Add `ReportSectionRenderer` component.
  - Import section components and `resolveSectionKind`.
  - Use dynamic `<component :is="...">` to dispatch.
  - Unknown or not-yet-implemented kinds render as `GenericSection`.
  - Overview, trend, and recommendation kinds MAY render as `GenericSection` until dedicated components are added in Phase 7b.

- [x] 7.7 Add `ModuleSection` component.
  - Render section header (title + summary).
  - Render metric cards row.
  - Render frame grid or mixed media or chart grid based on `resolveModuleLayout`.
  - Render findings block.
  - Render recommendations block.

- [x] 7.8 Add `GenericSection` component.
  - Render title, metrics, findings, recommendations, assets, charts in a simple vertical stack.
  - No special layout logic.

- [x] 7.9 Add shared card and chart components.
  - `MetricCard`: label, value, unit, level badge.
  - `FindingList`: list of findings with severity badge.
  - `RecommendationList`: list of recommendation items.
  - `ReportRadarChart`: migrate existing ECharts radar from ReportView into this component.
  - `ReportChart`: render generic chart config (line/bar) as fallback table in Phase 7a; ECharts upgrade deferred to Phase 7b.

- [x] 7.10 Refactor `ReportView.vue`.
  - Keep page-head, loading, error, empty states.
  - Keep Element Plus components for buttons, tags, empty, provenance descriptions.
  - Replace the hardcoded `grid-two` body with normalized section rendering via `ReportSectionRenderer`.
  - Remove the old `grid-two` body layout after adapter-based rendering is in place.
  - Do not render the legacy metrics/diagnostics grid below the new section flow.
  - Move ECharts radar rendering into a separate `ReportSummaryPanel.vue`.

- [x] 7.11 Add `ReportSummaryPanel` component.
  - Receive normalized summary data.
  - Render overall score if present.
  - Render ECharts radar chart if `summary.radar` has data.
  - Render top findings and priority issues if present.
  - Do not crash if radar data is empty.

## Phase 7b: Visual compatibility and demo support

- [x] 7.12 Add `EvidenceFrameCard` component.
  - Render frame label, value badge, image, caption.
  - Handle missing image URL gracefully (show placeholder).

- [x] 7.13 Add swim-report.v1 demo fixture.
  - Keep existing `legacyDemoReport` unchanged.
  - Add `swimReportV1DemoReport` with `schema_version`, `sections` (overview, body_position, catch_pull, efficiency, recommendations), metrics, findings, recommendations.
  - Add chart config examples in efficiency section.

- [x] 7.14 Update `api.ts` report fetching for demo format selection.
  - Accept optional `{ demoFormat?: 'legacy' | 'swim_v1' }` parameter.
  - Missing or invalid demo format SHALL fall back to `legacy`.
  - Forward to `getDemoReport` with format selection.
  - Read `?demo_format` from route query.

- [x] 7.15 Update `demoData.ts` `getDemoReport()` function.
  - Accept format parameter.
  - Return `swimReportV1DemoReport` when format is `swim_v1`.
  - Missing or invalid format SHALL return existing legacy demo report.

- [x] 7.16 Add responsive report section layouts.
  - 3-column frame grid collapses to 1 column below 768px.
  - Mixed media layout stacks vertically on narrow screens.
  - Chart grid remains readable on mobile.

- [x] 7.17 Add compatibility verification.
  - Legacy demo report renders without error, shows radar chart.
  - swim-report.v1 demo report renders all sections.
  - Sections without `type` render by key mapping.
  - Unknown section keys render with `GenericSection`.
  - Empty assets/charts/diagnostics do not crash the page.
