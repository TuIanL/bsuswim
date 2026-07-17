## Why

系统已经能够将 CVAT Skeleton XML 自动解析为包含 COCO17 左右分侧关键点的 NormalizedAnnotation，但当前 side-view metrics 引擎面向带有水面线、标尺、动作事件和距离标记的技术分析场景，且读取 shoulder/elbow/wrist 等非分侧关键点。真实 CVAT 输入主要包含逐帧的 left/right 分侧点，缺乏事件和标尺。需要新增一套只依赖二维骨架、无需动作事件或距离标尺的确定性运动学计算器，把逐帧关节点转换为可追溯、可降级、可被后续绘图和报告装配消费的四类基础指标。

## What Changes

- 新增 `side_2d_kinematics` calculator（与旧 `side_view_metrics` 并存）
- 新增 `swim-side-kinematics.v1` 输出 schema
- 新增 calculator registry，替代硬编码 calculator 路由
- 新增 COCO17 左右分侧骨架适配层 `CanonicalKinematicFrame`
- 生成肩中点、髋中点、踝中点、躯干中点、头部中心等合成关节点，含 `construction_mode`（bilateral_midpoint / left_proxy / right_proxy / unavailable）
- 实现四类二维运动学指标：身体姿态与稳定性、上肢、下肢、头部与躯干控制
- 每个指标输出统一的 `MetricEnvelope`（value、unit、sample_count、availability、confidence、source_frames、reference_basis）
- 输出 summary / time_series / ranges / representative_frames / quality
- 复用现有 `annotation_metrics` 表，新增 `source_revision` 列
- 扩展 `calculate-metrics` API：支持 `?calculator=` 参数
- 扩展现有 GET .../metrics 端点，增加 calculator 和 calculator_version 参数，默认 side_view_metrics
- 保留旧 `side_view_metrics` calculator，不改动已有诊断和报告

## Capabilities

### New Capabilities

- `side-2d-kinematics`: 从侧面 COCO17 二维骨架计算四类运动学指标，支持左右分侧、遮挡/缺失点回退、construction_mode 追踪、逐指标可用性和置信度

### Modified Capabilities

- `side-view-metrics`: calculate-metrics API 支持 calculator 参数；metrics 查询必须按 calculator 过滤；annotation_metrics 保存实际 schema_version、source_revision，排序按 updated_at DESC
- `backend-platform-core`: 新增 calculator registry 和 GET metrics 端点

## Impact

- `backend/app/services/metrics/engine.py` — registry 路由
- `backend/app/services/metrics/kinematics/` — 新 calculator 模块
- `backend/app/services/metrics/geometry.py` — 新增 signed_line_tilt_deg
- `backend/app/schemas/metrics.py` — 新增 MetricEnvelope 等
- `backend/app/models/annotation_metric.py` — 新增 source_revision
- `backend/app/services/metrics_service.py` — 路由、持久化、查询
- `backend/app/api/routes/metrics.py` — calculator 参数、GET 端点
- `backend/app/services/metrics/quality.py` — 新 quality evaluator
- `backend/app/services/metrics/continuity.py` — 新增
- `backend/tests/` — 合成 fixture + golden fixture + 全部指标测试
- Alembic migration
- 不修改 diagnostics engine、report builder、前端
