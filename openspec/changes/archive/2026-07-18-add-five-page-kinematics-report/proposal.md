## Why

系统已经从侧面 COCO17 骨架生成三类独立产物：`AnnotationMetric(swim-side-kinematics.v1)`（四类二维运动学指标）、`KinematicArtifactSet(swim-kinematic-artifacts.v1)`（关键帧与五类图）、`KinematicReviewFindingSet(swim-2d-review-findings.v1)`（待复核发现）。它们目前仍通过独立 API 读取，尚未形成一份教练可阅读的结构化报告。

现有 `build_swim_report_data()` 面向旧 `swim-side-metrics.v1` 与 `AnalysisResult.diagnostics`，其 section key、指标结构和数据来源均与新的二维运动学链路不一致，section 也没有页码、页面类型和模块字段。需要新增固定五页的二维运动学报告 profile，将三类已持久化产物装配为可追溯、可降级、可供前端与 PDF 使用的 `swim-report.v1`。本 Change 只做纯装配服务与预览接口，不写入 `ReportMetadata`（留给 Change 7）。

## What Changes

- 新增报告 profile：`side_2d_kinematics_5page_v1`，固定输出五页 `swim-report.v1`
- 新增二维运动学五页报告装配器 `build_five_page_kinematics_report()` 与数据库输入服务 `assemble_five_page_kinematics_report()`
- 新增 artifact current resolver：`get_current_artifact_set()`，按 artifact 自有 expected signature 精确解析（与 findings 的 `get_current_review_findings()` 签名公式相互独立）
- section 显式包含 `page_number`、`page_type`、`module_key`、`source_module_keys`、`assets`、`metrics`、`findings`、`quality_notes`
- 报告顶层状态字段命名为 `assembly_status`，与上游 `artifact_set.status` / `finding_set.status` 严格区分
- 将 `MetricEnvelope` 投影为展示型 `ReportMetric`；第 2—5 页运动学数值统一从单一 `all_report_metrics` 索引取；第 1 页输入与覆盖统计通过独立的 `overview_stats` 构建（有效帧数、关节点完整率等不属于 23 个 canonical 指标），避免污染指标注册表
- 将 `KinematicArtifact` 投影为 `ReportAsset`，保留完整追溯字段；`skipped` / `failed` 资产转为 `quality_notes`
- 将 `KinematicReviewFinding` 按 category 分配到第 2—5 页，第 5 页保留保守语义（不输出诊断或训练处方）
- 雷达图语义（含免责声明）只能从 `KinematicArtifactSet.manifest` 透传，报告层不得硬编码
- 缺少当前 artifacts 或 review findings 时生成 `partial` 报告（顶层 `assembly_status = partial`）
- 指标过期或 schema 不受支持时拒绝生成，返回明确错误码
- 新增按 `annotation_metric_id` 调用的认证 API，返回完整五页 JSON，不持久化 `ReportMetadata`
- 保留现有 legacy `build_swim_report_data()` 行为不变

## Capabilities

### New Capabilities

- `five-page-kinematics-report`：将 `swim-side-kinematics.v1`、当前视觉资产与当前待复核发现，装配为固定五页的 `swim-report.v1`；支持缺少非必要产物时的 partial 降级；支持输入版本追溯与幂等报告签名。

### Modified Capabilities

- `report-data-assembly`：增加 `side_2d_kinematics_5page_v1` 报告 profile；新 profile 的 `section.module_key` 为页面聚合键，与旧 `side_technical` 的 section key 互不兼容；明确两套 profile 独立存在，旧 `side_technical` 路径保持不变。

## Impact

- `backend/app/services/reporting/kinematics_report/`（新增装配层）
- `backend/app/schemas/kinematics_report.py`（新增）
- `backend/app/services/kinematic_artifacts/resolver.py`（新增 `get_current_artifact_set`）
- `backend/app/services/kinematic_artifacts/signature.py`（抽取可复用 expected-signature 计算，不改动最终公式）
- `backend/app/api/routes/kinematics_reports.py`（新增）
- `backend/app/services/report_builder.py`（导出新装配入口，旧函数行为不变）
- `backend/app/api/router.py`（注册路由）
- OpenSpec capability specs
- 单元测试、契约测试、golden fixture 测试

## Non-Goals

- 不修改指标计算算法，不重新绘制任何图表，不重新运行 review findings 规则
- 不将 findings 写入 `AnalysisResult.diagnostics`，不生成确定性技术诊断
- 不生成力量、推进效率或训练处方结论
- 不修改前端 section renderer，不实现 PDF 导出
- 不创建 annotation-driven `AnalysisTask` / `AnalysisResult`，不写入 `ReportMetadata`
- 不在报告层重写或硬编码雷达图免责声明（只能透传 manifest）
- 不抽象出统一的 `get_current_generated_set()`，artifacts 与 findings 的签名公式保持独立
