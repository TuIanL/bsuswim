## Context

`frontend-vue` 当前是 Vue 3 + TypeScript + Vite + Element Plus + Pinia + Axios + ECharts 的平台前端，已有 `/upload`、`/tasks`、`/workspace/:taskId`、`/reports/:taskId` 等页面。现有页面仍以旧的单视频 `AnalysisTask` 模型为中心，而业务后端已经提供以用户、运动员、训练记录和训练记录视频绑定为核心的 REST API。

本次设计目标是把 `frontend-vue` 从“分析任务演示页”推进为第一批可联调业务页面：登录注册、运动员列表、运动员档案、测试任务创建、多机位上传。它需要继续保留 demo 模式，方便没有后端时演示页面结构和流程。

## Goals / Non-Goals

**Goals:**

- 以 `frontend-vue` 为唯一前端实现目标，不改造 `frontend` Next.js 应用。
- 建立 Vue 侧认证会话模型，包括 token 保存、当前用户恢复、Axios 鉴权头和路由守卫。
- 将前端业务模型对齐后端：`User`、`Athlete`、`TrainingSession`、`VideoFile`、`SessionVideo`。
- 支持教练完成核心闭环：登录或注册、查看或创建运动员、打开档案、创建测试任务、上传多机位视频、进入后续工作台或报告。
- 继续使用 Element Plus 构建表格、表单、弹窗、上传控件、标签、描述列表和状态展示。
- 保留 ECharts 用于档案趋势预览，并为第二批仪表盘页面预留图表组织方式。
- 保留 demo 模式，未配置 `VITE_API_BASE_URL` 时不阻断页面浏览。

**Non-Goals:**

- 不在本次变更中实现第二批指标仪表盘页和诊断报告页的完整 PPT 还原。
- 不新增后端接口，不改变数据库表结构。
- 不引入 React、Next.js、Ant Design 或 Tailwind CSS 到 `frontend-vue`。
- 不实现真实多机位时间轴同步、帧级校准或 Video.js 帧控制；本次只预留 `sync_offset_ms` 和机位绑定数据。
- 不实现管理员后台完整功能；管理员角色仅做路由和导航预留。

## Decisions

### 1. 使用 Pinia 拆分认证和业务状态

认证状态放入 `auth` store，负责 `access_token`、用户资料、登录、注册、登出、恢复会话。运动员和测试任务数据可以使用轻量 store 或页面内加载，优先保证 API client 类型清晰。

替代方案是所有页面各自读取 localStorage 和调用 API。该方式初期更快，但会让路由守卫、鉴权头和登录过期处理分散，后续维护成本高。

### 2. API client 以真实后端资源为主，demo 模式走同名函数

`frontend-vue/src/services/api.ts` 应暴露面向业务资源的函数，例如 `login`、`register`、`getCurrentUser`、`listAthletes`、`createAthlete`、`getAthlete`、`listAthleteSessions`、`createSession`、`uploadVideo`、`bindSessionVideo`、`listSessionVideos`。在 demo 模式下，这些函数返回本地模拟数据，并尽量保持响应结构接近真实后端。

替代方案是继续沿用 `/tasks` 函数并在页面层做转换。该方式会把旧模型继续固化到新页面中，不利于后续联调。

### 3. 路由按业务闭环组织

建议路由：

- `/login`
- `/register`
- `/athletes`
- `/athletes/:athleteId`
- `/sessions/new`
- `/sessions/:sessionId/upload`
- `/tasks`
- `/workspace/:taskId`
- `/reports/:taskId`

`/` 默认进入 `/athletes`。未登录且非 demo 模式时只能访问 `/login` 和 `/register`；已登录用户访问登录注册页时跳转到 `/athletes`。demo 模式可以自动使用演示用户，避免展示时卡在认证页。

### 4. 多机位上传页以 TrainingSession 为上下文

上传页不再创建旧 `AnalysisTask`，而是读取或展示当前 `TrainingSession`，为固定机位槽位上传视频：

- `side`
- `front`
- `top`
- `underwater`
- `semi_underwater`

每个槽位上传成功后先调用 `/videos/upload` 得到 `VideoFile`，再调用 `/sessions/:sessionId/videos` 绑定 `view_type`、`fps`、`resolution`、`sync_offset_ms`。提交分析按钮可以在本次先作为后续入口预留，至少要能区分“保存草稿”和“已具备提交分析条件”。

### 5. 复用现有视觉语言，但提高业务后台信息密度

`frontend-vue` 已采用 Element Plus 和暗色平台样式。新增页面应继续使用左侧导航、主内容区、卡片化区块和紧凑表单，但避免营销式大标题。运动员列表、档案和任务创建页应优先满足教练高频操作：搜索、筛选、查看、创建测试。

## Risks / Trade-offs

- [Risk] 后端 `AthleteRead` 当前没有队伍名称、最近测试时间、当前技术评分等列表所需字段 → 前端先以现有字段展示，缺失字段使用本地派生、demo 数据或占位状态，并把真实后端增强留到后续变更。
- [Risk] 后端 `ViewType` 枚举是否已经包含 `front`、`top`、`semi_underwater` 需要实现时核对 → 前端类型先按需求定义，若后端枚举不足，实施阶段需选择映射或补后端变更。
- [Risk] 旧工作台和报告仍依赖 `taskId`，而新流程使用 `sessionId` → 第一批只保证上传后能进入既有后续入口或显示“待分析”状态，不强行完成 session 到 analysis task 的完整重构。
- [Risk] demo 模式和真实 API 模式行为分叉过多 → API client 层保持函数同名、返回同形，页面避免直接判断大量 demo 细节。
- [Risk] 登录 token 存入 localStorage 有常见 XSS 风险 → 当前阶段按浏览器本地应用联调需要保存 token；后续若部署到公网，应评估 HttpOnly cookie 或更严格 CSP。

## Migration Plan

1. 先扩展类型和 API client，保留旧 `AnalysisTask` 相关函数，避免一次性破坏工作台和报告页面。
2. 新增 auth store 和路由守卫，再接入登录注册页面。
3. 新增运动员和测试任务页面，并把默认首页从 `/upload` 调整为 `/athletes`。
4. 将上传页迁移为 `/sessions/:sessionId/upload` 多机位上传；旧 `/upload` 可重定向到 `/sessions/new` 或显示选择运动员入口。
5. 回归验证 demo 模式和真实 API 模式的构建、登录、列表、创建、上传流程。

如需回滚，可保留旧路由和旧 API 函数，先恢复 `/upload` 与 `/tasks` 的默认入口；认证守卫应集中在 router 中，便于临时关闭。

## Open Questions

- 后端 `ViewType` 是否已经支持 `front`、`top`、`semi_underwater`，以及是否需要和既有枚举命名保持完全一致？
- 技术评分、最近测试时间、队伍名称是否将在后端列表接口中聚合返回，还是第一阶段由前端根据历史记录派生？
- 运动员角色登录后“只能查看自己的档案和报告”的身份绑定关系是否已有后端字段支持？
