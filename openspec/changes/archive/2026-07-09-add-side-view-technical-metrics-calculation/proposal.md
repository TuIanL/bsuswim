## Why

Change #1 建立了 `annotation_files` 持久化，Change #2 建立了 `normalized_annotations` 标准化标注层，Change #3 打通了 Kinovea 标注导入。但标注数据到技术报告之间仍缺一层：**标准化标注尚未被计算成结构化技术指标**。后续 Change #5（规则诊断）与 Change #6（报告装配）都需要可直接消费的事实指标作为输入，而不是重新解析关键点。

本 change 新增 side-view metrics engine，把 `normalized_annotations` 里的关键点、关键帧、标尺、事件、人工标签，计算成 `annotation_metrics` 中可被 diagnostics 与 report_builder 直接消费的结构化事实指标。它只产出测量值，不产出诊断结论。

## What Changes

- 新增 `backend/app/services/metrics/` 指标计算引擎：`geometry.py`（角度/距离/投影）、`quality.py`（缺字段校验）、`body_metrics.py` / `upper_limb_metrics.py` / `leg_metrics.py` / `rhythm_metrics.py`（四组指标）、`engine.py`（`calculate_side_view_metrics` 主入口）
- 新增 `backend/app/schemas/metrics.py`：`MetricValue`、`SideViewMetrics` 等 Pydantic schema，固定 `schema_version = "swim-side-metrics.v1"`
- 扩展 `normalized-annotation-schema`：新增 `reference_lines`（含 `waterline`）、`distance_markers`、`swim_direction` 三个字段，并补 alembic 迁移；quality checker 增加对它们的感知（缺 waterline 时 `hip_depth_cm` 降级为 warning）
- 新增 `annotation_metrics` 表与 ORM 模型、schema、alembic 迁移；持久化走 `annotation_metrics`，**不复用 `analysis_results`**
- 新增计算/调试端点 `POST /api/normalized-annotations/{id}/calculate-metrics?persist=` 与读取端点 `GET /api/normalized-annotations/{id}/metrics`（及 `GET /api/annotation-metrics/{id}`）
- 指标为纯事实测量，不含诊断句子；复合评分（如 `streamline_index`、`technical_stability_score`）仅为内部数值，不输出"身体位置偏低"类结论

## Capabilities

### New Capabilities
- `side-view-metrics`：从 `NormalizedAnnotation` 计算侧面视角技术指标（身体/上肢/腿部/节奏效率四组），输出固定 schema 并持久化到 `annotation_metrics`

### Modified Capabilities
- `normalized-annotation-schema`：新增 `reference_lines`、`distance_markers`、`swim_direction` 字段及迁移；quality checker 增加对 waterline 缺失的感知

## Impact

- 数据库：新增 `annotation_metrics` 表；`normalized_annotations` 表新增 `reference_lines`、`distance_markers`、`swim_direction` 三列（需迁移）
- 不修改 `analysis_tasks` / `analysis_results` 表结构，不接入 `ModelServiceClient` 模型服务管线
- 不修改 `AnalysisTask.input_type`（本 change 不引入该列）
- `report_builder.py` 遗留的 `body_line_score` / `rhythm_score` / `overall_score` 等分数键兼容问题**推迟到 Change #6 的 report data adapter** 处理，本 change 的 metrics schema 不为此做兼容
- 前端：新增两个读取 metrics 的端点；不改变现有标注读写结构
