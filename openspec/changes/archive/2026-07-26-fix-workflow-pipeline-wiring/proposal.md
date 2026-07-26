## Why

运动学分析工作流的管线代码（后端 pipeline、前端 API 调用）已经全部实现，但存在两个阻断性问题导致端到端流程无法真正跑通：

1. **annotationMetricId 硬编码为 1**：`KinematicsWorkflowPage.vue` 中 `annotationMetricId` 写死返回 `1`，导致 `KinematicsArtifactsPanel` 和 `KinematicsReviewPanel` 在真实数据下加载错误数据或 404。
2. **后端无启动脚本**：`start-web.command` 仅启动前端 Vite dev server，没有启动 FastAPI 后端。用户无法一键启动完整环境。

## What Changes

- 修复 `KinematicsWorkflowPage.vue` 中 `annotationMetricId` 的计算逻辑，从已完成分析任务的 `raw_result.products.annotation_metric_id` 动态获取真实 ID
- 新增 `start-backend.command` 脚本，一键启动 FastAPI 后端（含 uvicorn、数据库检查）
- 更新 `start-web.command` 同时启动前后端，或提供联合启动脚本

## Capabilities

### New Capabilities

- `e2e-pipeline-startup`: 端到端环境启动能力，包括前后端联合启动、数据库就绪检查

### Modified Capabilities

- `guided-side-2d-kinematics-workflow`: 工作流中运动学结果展示面板（指标/可视化/诊断）的 annotationMetricId 必须从分析任务结果动态解析，而非硬编码

## Impact

- **前端**：`KinematicsWorkflowPage.vue` 的 `annotationMetricId` 计算逻辑
- **启动脚本**：新增 `start-backend.command`，可能修改 `start-web.command`
- **后端无变更**：API 和 pipeline 代码无需修改，问题仅在前端接线和启动流程
