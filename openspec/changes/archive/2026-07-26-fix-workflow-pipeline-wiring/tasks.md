## 1. 后端 Schema 暴露 raw_result

- [x] 1.1 在 `backend/app/schemas/analysis.py` 的 `AnalysisResultRead` 中增加 `raw_result: dict = {}` 字段
- [x] 1.2 运行现有后端测试确认 schema 变更无破坏性

## 2. 前端 annotationMetricId 动态解析

- [x] 2.1 在 `useKinematicsWorkflow.ts` 中新增 `annotationMetricId` computed，从 `latestTask` 关联的 result `raw_result.products.annotation_metric_id` 提取
- [x] 2.2 修改 `KinematicsWorkflowPage.vue`，将 `annotationMetricId` 从 hardcoded `1` 改为使用 composable 返回的真实值
- [x] 2.3 确保 `KinematicsMetricsPanel`、`KinematicsArtifactsPanel`、`KinematicsReviewPanel` 在 `annotationMetricId` 为 null 时不发起请求

## 3. 启动脚本改造

- [x] 3.1 修改 `start-web.command`，在启动前端前先启动后端 uvicorn 进程
- [x] 3.2 在启动脚本中添加数据库就绪检查（docker postgres 容器 + alembic upgrade head）
- [x] 3.3 在启动脚本中设置 `VITE_API_BASE_URL=http://127.0.0.1:8000` 环境变量
- [x] 3.4 修改 `stop-web.command` 同时清理前后端进程

## 4. 验证

- [x] 4.1 执行 `start-web.command` 确认前后端均正常启动
- [x] 4.2 在浏览器中完成完整工作流：上传视频 → 上传 CVAT 标注 → 提交分析 → 确认三个结果面板使用真实数据
- [x] 4.3 确认 `stop-web.command` 正确清理所有进程
