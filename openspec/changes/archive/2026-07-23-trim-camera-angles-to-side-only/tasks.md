## 1. 移除上传页的"后续扩展机位"面板

- [x] 1.1 在 `frontend-vue/src/components/kinematics-workflow/KinematicsWorkflowPage.vue` 中删除 `<FutureCameraViewsPanel :videos="allVideos" />` 用法（模板底部）
- [x] 1.2 在同文件中删除 `import FutureCameraViewsPanel from './FutureCameraViewsPanel.vue'` 及其相关 `allVideos` 引用（如不再被其它逻辑使用）
- [x] 1.3 删除组件文件 `frontend-vue/src/components/kinematics-workflow/FutureCameraViewsPanel.vue`

## 2. 修正创建任务页的多机位文案

- [x] 2.1 修改 `frontend-vue/src/views/CreateSessionView.vue` 步骤说明，将"侧面、正面、俯视、水下与半水下视频"改为"上传侧面视频（本次仅分析侧面机位）"
- [x] 2.2 将同页"多机位视频上传"等措辞统一改为"侧面视频上传"，使创建页与上传页口径一致

## 3. 校验与收尾

- [x] 3.1 运行前端类型检查 / 构建，确认移除 import 后无编译错误（无残留 `FutureCameraViewsPanel` 引用）
- [x] 3.2 启动前端本地服务，进入上传页确认仅显示侧面视频上传入口、无任何其他机位卡片或占位区域
- [x] 3.3 确认后端 `view_type` 枚举与分析引擎未改动，本次为纯前端变更
