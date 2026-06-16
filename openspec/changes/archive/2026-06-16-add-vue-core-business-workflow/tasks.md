## 1. 类型与 API Client

- [x] 1.1 扩展 `frontend-vue/src/types.ts`，新增 `User`、`UserRole`、`AuthToken`、`Athlete`、`TrainingSession`、`SessionVideo`、`SessionVideoView`、`CreateSessionForm` 等业务类型
- [x] 1.2 调整 `frontend-vue/src/services/api.ts` 的 Axios client，支持 `VITE_API_BASE_URL`、`/api/v1` 前缀和 `Authorization: Bearer <access_token>` 注入
- [x] 1.3 新增认证 API 函数：`login`、`register`、`getCurrentUser`
- [x] 1.4 新增运动员 API 函数：`listAthletes`、`createAthlete`、`getAthlete`、`listAthleteSessions`
- [x] 1.5 新增测试任务和视频 API 函数：`createSession`、`listSessions`、`getSession`、`uploadVideo`、`bindSessionVideo`、`listSessionVideos`
- [x] 1.6 保留旧工作台和报告所需的 task/report client，避免破坏 `/workspace/:taskId` 和 `/reports/:taskId`

## 2. Demo 数据与兼容层

- [x] 2.1 扩展 `frontend-vue/src/services/demoData.ts`，加入 demo 用户、运动员、训练记录、历史评分、趋势指标和多机位视频数据
- [x] 2.2 让新增 API 函数在 demo 模式下返回同形 demo 数据
- [x] 2.3 为 demo 模式实现创建运动员、创建测试任务和绑定机位视频的本地状态更新
- [x] 2.4 确认未配置 `VITE_API_BASE_URL` 时登录、列表、档案、创建测试和上传页面均可浏览

## 3. 认证与路由权限

- [x] 3.1 新建 `frontend-vue/src/stores/auth.ts`，管理 token、当前用户、角色、登录、注册、恢复会话和登出
- [x] 3.2 新建 `LoginView.vue`，实现用户名、密码、记住登录状态和登录后跳转
- [x] 3.3 新建 `RegisterView.vue`，实现姓名、用户名、手机号、邮箱、密码和角色选择
- [x] 3.4 更新 `frontend-vue/src/router.ts`，添加 `/login`、`/register` 和全局路由守卫
- [x] 3.5 实现未登录访问保护页跳转 `/login`，已登录访问认证页跳转 `/athletes`
- [x] 3.6 在非教练角色下隐藏或禁用运动员管理、测试创建和多机位上传操作

## 4. 平台壳与导航

- [x] 4.1 更新 `frontend-vue/src/App.vue`，将侧边导航扩展为运动员、测试任务、视频上传、工作台、报告等业务入口
- [x] 4.2 将 `/` 默认入口调整为 `/athletes`
- [x] 4.3 在平台壳中展示当前用户、角色、API/demo 模式和登出入口
- [x] 4.4 调整移动端和窄屏导航样式，确保菜单、表格操作和表单控件不重叠
- [x] 4.5 保持现有暗色运动科技视觉风格和 Element Plus 组件一致性

## 5. 运动员列表与档案

- [x] 5.1 新建 `AthletesView.vue`，展示姓名、性别、年龄、主项、所属队伍、最近测试时间、当前技术评分和操作列
- [x] 5.2 在运动员列表顶部实现姓名搜索、泳姿筛选、队伍筛选和技术评分区间控件
- [x] 5.3 实现新建运动员弹窗或抽屉表单，并调用 `createAthlete`
- [x] 5.4 新建 `AthleteProfileView.vue`，展示基础信息、最近评分、历史测试记录和创建新测试按钮
- [x] 5.5 在运动员档案中使用 ECharts 展示核心指标趋势预览
- [x] 5.6 处理运动员不存在、无历史测试记录、加载失败和 demo 空状态

## 6. 测试任务创建

- [x] 6.1 新建 `CreateSessionView.vue`，支持选择运动员或读取 `athleteId` query 参数
- [x] 6.2 实现测试日期、泳姿、距离、泳池长度、场景和备注字段
- [x] 6.3 提交有效表单后调用 `createSession` 并跳转 `/sessions/:sessionId/upload`
- [x] 6.4 处理未选择运动员、提交失败和后端校验错误提示
- [x] 6.5 从运动员列表和运动员档案接入创建测试入口

## 7. 多机位上传

- [x] 7.1 将上传流程迁移为 `SessionUploadView.vue` 或重构现有 `UploadView.vue`，路由为 `/sessions/:sessionId/upload`
- [x] 7.2 在上传页顶部展示当前 `TrainingSession` 的运动员、日期、泳姿、距离、泳池长度和状态
- [x] 7.3 实现侧面、正面、俯视、水下、半水下五个机位上传卡片
- [x] 7.4 每个机位卡片支持选择视频、显示文件名和文件大小、上传状态、失败重试和 `sync_offset_ms` 输入
- [x] 7.5 上传机位视频时依次调用 `uploadVideo` 和 `bindSessionVideo`
- [x] 7.6 实现保存草稿动作，保持当前绑定视频和同步偏移状态
- [x] 7.7 实现提交分析动作的前端校验：至少一个机位视频成功绑定；后端分析未接入时给出明确提示

## 8. 任务管理与旧页面衔接

- [x] 8.1 调整 `TasksView.vue`，优先展示 `TrainingSession` 或 session 级任务数据
- [x] 8.2 对待上传、已上传、分析中、已完成、失败等状态提供清晰标签和下一步操作
- [x] 8.3 为待上传 session 跳转 `/sessions/:sessionId/upload`
- [x] 8.4 为已完成或已有分析结果的记录保留进入 `/workspace/:taskId` 和 `/reports/:taskId` 的入口
- [x] 8.5 保持旧工作台和报告页面可运行，不在本次强制改为 session 路由

## 9. 验证

- [x] 9.1 运行 `npm run build` 或 `npm run typecheck` 等可用检查，确认 TypeScript 和 Vue 构建通过
- [x] 9.2 启动 `frontend-vue` dev server，验证 demo 模式核心路径：登录或 demo 进入、运动员列表、档案、创建测试、多机位上传、任务管理
- [x] 9.3 在配置后端 API 的环境下验证真实登录、当前用户恢复、运动员列表、创建运动员、创建训练记录和视频上传绑定
- [x] 9.4 检查桌面和移动端关键页面，确认导航、表格、表单、上传卡片和按钮没有文本溢出或重叠
