## Why

当前训练记录上传页面仍以"多机位视频上传"为中心，用户需要自行理解：哪个机位是二维运动学分析真正需要的输入、标注是否解析、标注质量是否允许分析、哪些运动学模块可计算、分析任务执行到哪一阶段、失败后应如何恢复、报告在哪里查看与导出。

系统已具备 CVAT XML ingestion、质量门禁、四类指标、五类可视化资产、复核发现、五页报告以及完整的 `annotation_kinematics` pipeline，但这些后端能力尚未被组织成一个面向普通用户的完整 Web 工作流。当前页面还允许"任一机位视频上传成功"后提交分析，容易让用户误以为正面、俯视、水下和半水下机位已进入 MVP 自动报告能力。

## What Changes

- 将 `/sessions/:sessionId/upload` 重构为六步侧面二维运动学引导流程：上传绑定侧面视频、上传 CVAT Skeleton XML、自动解析并展示标注质量、确认四类运动学模块可用状态、提交并跟踪 `annotation_kinematics` 分析任务、查看 HTML 报告或导出/下载 PDF。
- 主流程只突出侧面机位；正面、俯视、水下、半水下改为只读的"后续扩展能力"区域。
- 展示标注解析摘要、质量分数、质量问题和建议操作；展示身体姿态、上肢、下肢、头躯干四类模块的预计可用状态。
- 显式提交 `pipeline_type = annotation_kinematics`、`pipeline_version = side_2d_v1`。
- 提交后停留在当前页面持续轮询分析任务，不再立即强制跳转工作台。
- 展示流水线内部阶段、已完成步骤、当前步骤和失败步骤；根据错误类型提供"重试当前任务"或"使用最新标注重新生成"。
- 报告完成后提供 HTML 报告和 PDF 操作入口；页面刷新后从服务端恢复当前视频、标注、任务和报告状态。
- 对现有 API 做最小读取契约扩展，不修改指标、资产、发现和报告生成逻辑。
- 后端新增活跃任务并发防重（同一 session 下仅允许一个活跃 `annotation_kinematics` 任务，命中抛领域异常并由路由映射 HTTP 409），并统一 `AnalysisTaskRead` 与 `AnalysisStatusRead` 的流水线进度投影（按 pipeline_type 选择阶段规范，兼容 model_service）；`resubmit` 复用现有 submit 端点且仅由前端提交 `normalized_annotation_id`，revision 由后端锁定；不新增重解析端点（复用 `POST /annotations/{annotation_file_id}/parse`）。

## Capabilities

### New Capabilities
- `guided-side-2d-kinematics-workflow`: 系统提供一个可恢复的六步侧面二维运动学 Web 工作流，根据服务端持久化状态推导当前步骤，并明确区分输入质量、任务执行状态和报告新鲜度。

### Modified Capabilities
- `automatic-annotation-ingestion-workflow`: 标注列表响应需提供刷新后恢复解析摘要、质量详情与四类模块可用状态所需的数据。
- `annotation-driven-analysis-pipeline`: 任务读取接口需暴露统一的流水线进度（类型、版本、执行步骤、失败步骤、错误码、actions），前端据此展示真实进度；失败任务需按错误类型区分 `retry` 与 `resubmit`。
- `swim-interactive-performance-report`: 引导工作流在报告完成后提供 HTML 和 PDF 入口；本 Change 不修改报告 section renderer 或五页报告结构。

## Impact

### Frontend
- `frontend-vue/src/views/SessionUploadView.vue`
- `frontend-vue/src/views/WorkspaceView.vue`
- `frontend-vue/src/services/api.ts`
- `frontend-vue/src/types.ts`
- 新增 `frontend-vue/src/components/kinematics-workflow/`
- 新增 `frontend-vue/src/composables/useKinematicsWorkflow.ts`
- 新增 `frontend-vue/src/utils/kinematicsWorkflow.ts`

### Backend
- `backend/app/schemas/annotation.py`
- `backend/app/schemas/analysis.py`
- `backend/app/api/routes/analysis.py`
- `backend/app/api/routes/normalized_annotations.py`（复用已有 parse 端点）
- `backend/app/services/analysis_service.py`
- `backend/app/services/annotation_ingestion_service.py`（或 repository/projection）

### Tests
- 后端读取契约测试（标注列表、任务状态、并发防重、retry/resubmit 分类、重解析）
- 前端状态推导单元测试
- 工作流组件测试
- 视频、标注、分析、报告端到端测试
