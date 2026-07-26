## Context

当前 `KinematicsWorkflowPage.vue` 中 `annotationMetricId` 写死为 `1`，导致分析完成后的三个结果面板（指标/可视化/诊断）在真实数据下无法正确加载。

后端 `annotation_kinematics` pipeline 在 `saving_result` 阶段将 `annotation_metric_id` 写入 `AnalysisResult.raw_result.products.annotation_metric_id`，但 `AnalysisResultRead` schema 未暴露 `raw_result` 字段，前端无法获取。

启动方面，`start-web.command` 仅启动前端 Vite dev server，后端 FastAPI 需手动启动。

## Goals / Non-Goals

**Goals:**
- 前端运动学结果面板使用真实 `annotation_metric_id`
- 提供一键启动前后端的脚本
- 保持现有 API schema 的向后兼容

**Non-Goals:**
- 不修改后端 pipeline 逻辑
- 不修改数据库 migration
- 不重构前端组件架构

## Decisions

### Decision 1: 从 AnalysisResult.raw_result 获取 annotation_metric_id

**方案**: 在 `AnalysisResultRead` schema 中增加 `raw_result` 字段，前端从 `completedTask` 的关联 result 中提取 `products.annotation_metric_id`。

**备选方案**:
- 从 metrics endpoint 反查（需额外请求，增加延迟）
- 在 task response 中直接加字段（污染 task schema）

**选择理由**: `raw_result` 已存在于数据库，仅需 schema 暴露。前端已有 workspace 接口返回 result 数据，或可单独请求 result。

### Decision 2: 前端提取逻辑放在 composable 中

在 `useKinematicsWorkflow` 中新增 `annotationMetricId` computed 属性，从 `latestTask` 关联的 result 中提取。`KinematicsWorkflowPage` 消费此值传递给子面板。

### Decision 3: 联合启动脚本

修改 `start-web.command`，在启动前端前先启动后端 uvicorn。后端启动命令: `uvicorn app.main:app --host 127.0.0.1 --port 8000`。

**备选方案**: 新增独立 `start-backend.command`。

**选择理由**: 单一脚本降低用户认知负担，且 `stop-web.command` 可同时清理两个进程。

## Risks / Trade-offs

- [raw_result 字段体积] → pipeline 结果中 raw_result 可能较大，但仅在 result 接口返回，不影响列表接口性能
- [启动脚本依赖] → 后端需要 PostgreSQL 运行，脚本中需检查 docker 状态
