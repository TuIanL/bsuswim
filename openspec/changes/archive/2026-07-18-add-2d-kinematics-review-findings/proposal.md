## Why

系统已经能够从侧面 COCO17 骨架计算 `swim-side-kinematics.v1` 四类二维运动学指标，并生成关键帧和图表资产，但这些产物仍只是事实测量，尚不能自动形成教练可阅读、可复核的技术发现。现有 `side_freestyle_v1` 诊断规则面向旧 `swim-side-metrics.v1`，依赖水面线、标尺、动作阶段、划幅和 SWOLF 等语义指标，无法直接消费新的 `MetricEnvelope` 输出。需要新增一套有限、保守、可解释的 review findings 能力，把二维指标转换为待复核发现（含证据、证据帧、置信度、限制与复核问题），且不得包装成确定性技术诊断。

## What Changes

- 新增规则包 `side_2d_kinematics_v1`（`output_kind: review_finding`）
- 新增 `Side2DKinematicsReviewAdapter`，将 `MetricEnvelope` 展平为稳定标量上下文
- 新增 `KinematicReviewFindingsEngine`，复用既有结构化条件评估器
- 新增结构化 `KinematicReviewFinding` 输出 schema（status 恒为 `review_required`）
- 新增指标证据与证据帧解析器（持久化序列优先，标注回读仅用于定位画面）
- 新增八类待复核发现 KRF001–KRF008
- 对像素距离指标使用参考体长归一化，不使用固定像素阈值
- 基于指标 availability 与 confidence 计算发现置信度
- 新增 `kinematic_review_finding_sets` 持久化表
- 新增按 `annotation_metric_id` 生成与读取 findings 的 API
- 保留现有 `side_freestyle_v1` 与 AnalysisResult diagnostics 链路
- 本 Change 不把 findings 写入 AnalysisResult；由后续 pipeline Change 完成接线

## Capabilities

### New Capabilities

- `2d-kinematics-review-findings`: 从 `swim-side-kinematics.v1` 生成有限、可解释的待复核发现，每条包含指标证据、证据帧、置信度、限制与复核问题，支持幂等生成、版本追溯与 stale revision 拒绝。

### Modified Capabilities

- `rule-based-diagnostics`: RuleRegistry 支持声明 `output_kind: review_finding`；旧 `diagnostic` 规则集行为保持不变；公共条件评估器可被 review findings 引擎复用。

## Impact

- `backend/app/services/diagnostics/review_findings/`
- `backend/app/services/diagnostics/rules/side_2d_kinematics_v1.yaml`
- `backend/app/models/kinematic_review_finding.py`
- `backend/app/schemas/kinematic_review_finding.py`
- `backend/app/api/routes/kinematic_review_findings.py`
- `backend/app/services/diagnostics/registry.py`（新增 `output_kind` 校验）
- Alembic migration
- 单元测试、集成测试与真实 fixture 测试

## Non-Goals

- 不输出确定性技术诊断
- 不输出力量不足、推进力不足等原因结论
- 不生成正式训练处方
- 不修改旧 `side_freestyle_v1`
- 不写入 `analysis_results.diagnostics`
- 不接入五页报告
- 不修改前端
