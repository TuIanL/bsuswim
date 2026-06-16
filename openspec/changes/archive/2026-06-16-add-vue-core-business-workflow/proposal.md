## Why

当前 `frontend-vue` 仍以“单视频分析任务”为中心，无法支撑教练从登录、管理运动员、创建测试任务到多机位视频上传的核心业务闭环。后端已经提供 `auth`、`athletes`、`sessions`、`videos` 等 REST API，现在需要让 Vue 前端对齐真实业务对象，为后续指标仪表盘、诊断报告和长期追踪页面打基础。

## What Changes

- 在 `frontend-vue` 新增登录、注册、用户会话保持和角色感知路由守卫。
- 将 Vue 平台导航从单一“视频分析/任务管理”扩展为业务系统导航，包含运动员、测试任务、多机位上传、工作台和报告入口。
- 新增运动员列表页，支持姓名、泳姿、队伍、技术评分区间等筛选形态，并提供新建运动员、查看档案、创建测试入口。
- 新增运动员档案页，展示基础信息、最近技术评分、历史测试记录和核心指标趋势预览。
- 新增测试任务创建页，连接运动员和视频上传流程，创建成功后跳转到对应测试任务的上传页。
- 将现有上传体验重构为多机位测试视频上传页，支持侧面、正面、俯视、水下、半水下机位，并为每个视频保留 `sync_offset_ms`。
- 调整 `frontend-vue` API client 和类型定义，使其优先对接现有后端 `/api/v1/auth`、`/api/v1/users/me`、`/api/v1/athletes`、`/api/v1/sessions`、`/api/v1/videos/upload`、`/api/v1/sessions/:id/videos`。
- 保留 demo 模式，使未配置后端 API 时仍可浏览核心页面和流程样例。
- 不改造 `frontend` Next.js 应用；本次变更范围限定在 `frontend-vue`。

## Capabilities

### New Capabilities

- `vue-auth-session-access`: 覆盖 `frontend-vue` 的登录注册、token 保存、用户资料恢复、角色感知导航和路由权限。
- `vue-core-business-workflow`: 覆盖 `frontend-vue` 的运动员管理、运动员档案、测试任务创建、多机位上传和第一批业务闭环页面。

### Modified Capabilities

- `swim-analysis-platform-navigation`: 平台导航需要从单视频分析入口扩展到 Vue 业务后台入口，并保持已有暗色运动科技风格与响应式稳定性。
- `swim-video-analysis-job-flow`: 前端任务流程需要从旧的单视频 `AnalysisTask` 视角对齐到后端 `TrainingSession` + `SessionVideo[]` 视角，并保留进入工作台和报告的后续入口。

## Impact

- 主要影响 `frontend-vue/src/router.ts`、`frontend-vue/src/App.vue`、`frontend-vue/src/types.ts`、`frontend-vue/src/services/api.ts`、`frontend-vue/src/services/demoData.ts`、`frontend-vue/src/stores/`、`frontend-vue/src/views/` 和全局样式。
- 需要使用现有依赖 Vue Router、Pinia、Axios、Element Plus、ECharts；不新增 Ant Design 或 React 依赖。
- 需要前端请求携带 `Authorization: Bearer <access_token>`，并处理未登录、登录过期、角色差异和 demo 模式。
- 后端 API 暂不要求新增接口；若筛选字段后端尚未支持，前端可先本地筛选或以 UI 预留方式实现。
