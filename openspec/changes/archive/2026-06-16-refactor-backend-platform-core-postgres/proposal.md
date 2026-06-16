## Why

当前后端仍以“上传单个视频并创建分析任务”为主线，数据库配置也停留在 MySQL；这已经不足以支撑智泳云枢按运动员、训练记录、多机位视频、AI 分析和报告追踪的真实平台形态。现在需要一次清晰的后端核心层重构，把业务中心从 `video_id` 提升到 `session_id`，并统一切换到 PostgreSQL 与可迁移的数据模型。

## What Changes

- **BREAKING** 将业务数据库从 MySQL 切换为 PostgreSQL，并移除对 MySQL 驱动和连接串的默认依赖。
- 引入 Alembic 作为数据库迁移边界，后续平台表结构变化通过 migration 管理。
- 新增认证与当前用户能力，提供注册、登录、`/users/me` 等 JWT 认证 API。
- 新增运动员档案与训练记录能力，以 `athletes` 和 `training_sessions` 作为平台业务主线。
- 新增 `session_videos` 关系层，将上传的视频文件按训练记录、机位类型、同步偏移等业务角色绑定。
- **BREAKING** 将分析任务从单视频级 `video_id` 任务迁移为训练记录级 `session_id` 任务。
- 规范后端 REST API 命名到 `/api/v1/auth`、`/users`、`/athletes`、`/sessions`、`/videos`、`/analysis`、`/reports`。
- 保留现有本地上传、模型服务调用、结果保存和报告数据生成能力，但改为围绕训练记录组织。

## Capabilities

### New Capabilities

- `backend-platform-core`: 覆盖 PostgreSQL 后端平台核心层、认证、运动员档案、训练记录、多机位视频绑定、session 级分析和报告 API。

### Modified Capabilities

- `heavy-model-analysis-architecture`: 后端持久化数据库要求从 MySQL 改为 PostgreSQL，并明确业务后端通过 migration 管理平台核心表。
- `swim-video-analysis-job-flow`: 真实后端分析任务创建从“上传视频后创建视频级任务”改为“创建训练记录、绑定视频后提交 session 级分析任务”。
- `swim-visual-analysis-workspace`: 工作台加载真实任务时需要从 session 级分析结果与训练记录视频关系中获取视频资源和上下文。
- `swim-interactive-performance-report`: 报告读取从任务级报告扩展为 session 级报告，报告内容关联运动员、训练记录和分析结果。

## Impact

- 后端配置与依赖：`backend/requirements.txt`、`backend/app/core/config.py`、`.env.example`、`docker-compose.yml`。
- 数据库与 migration：新增 Alembic 配置和 PostgreSQL 初始 migration；停止用 `Base.metadata.create_all` 管理正式表结构。
- 后端模型与 schemas：拆分 `models.py`、`schemas.py` 为按领域组织的模块，并新增 users、teams、athletes、training_sessions、session_videos 等模型。
- API 路由：新增 `auth`、`users`、`athletes`、`sessions`、`analysis` 路由，调整现有 `videos`、`tasks`、`reports` 路由契约。
- 服务层：调整分析任务创建、模型服务请求 payload、分析结果保存、报告构建逻辑，使其围绕 `session_id` 工作。
- 前端集成：后续真实后端调用需要从旧 `/tasks` 流程迁移到 `/analysis` 与 `/sessions` 流程。
