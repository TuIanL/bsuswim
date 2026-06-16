## Context

当前业务后端已经具备 FastAPI app、SQLAlchemy session、本地视频上传、分析任务、模型服务调用和报告元数据保存能力，但核心模型仍是“一个视频对应一个分析任务”。这使得后续运动员档案、一次训练的多机位视频、长期训练追踪、session 级报告都缺少稳定业务中心。

本次重构把后端核心域模型调整为“用户 / 运动员 / 训练记录 / 视频文件 / 训练记录视频绑定 / 分析任务 / 报告”，并将数据库默认环境切换为 PostgreSQL。现有模型服务仍作为独立 FastAPI 服务存在，业务后端继续负责 API、认证、数据库状态、文件引用、结果保存和报告数据构建。

## Goals / Non-Goals

**Goals:**

- 使用 PostgreSQL 作为业务后端默认数据库，并提供本地 Docker Compose 开发环境。
- 使用 Alembic 管理数据库 schema，不再依赖应用启动时自动 `create_all`。
- 建立 JWT 认证与当前用户接口，支撑教练账号登录后的私有数据访问。
- 建立运动员档案、训练记录和 session 视频绑定模型。
- 将分析任务从 `video_id` 级别迁移为 `session_id` 级别。
- 规范 REST API 命名，使前端能够围绕训练记录创建、上传、绑定、提交分析和读取报告。
- 保留现有本地 `uploads` 存储边界，后续可迁移到 MinIO。

**Non-Goals:**

- 不在本次实现完整 RBAC、团队成员邀请、运动员自助登录或多租户计费。
- 不实现 PDF 导出、对象存储替换、Celery + Redis 生产队列或完整异步回调鉴权。
- 不要求一次性迁移历史 MySQL 数据；当前项目仍处于原型到平台骨架过渡阶段。
- 不在业务后端直接加载 YOLO 类重模型。

## Decisions

### 使用 PostgreSQL + psycopg 作为同步 SQLAlchemy 驱动

后端当前使用同步 SQLAlchemy `create_engine` 和同步 `Session`，因此第一阶段选择 `postgresql+psycopg`，避免同时引入 async SQLAlchemy、async session 生命周期和路由改写。

替代方案是 `asyncpg`。它更适合全异步栈，但会放大本次重构范围，并且当前模型服务调用、文件上传和数据库 service 已经按同步 session 组织。

### 使用 Alembic 管理 schema 演进

平台核心表会快速增加和调整，继续使用 `Base.metadata.create_all` 会让数据库状态不可追踪。Alembic 作为 migration 边界，可以把 users、athletes、training_sessions、session_videos、analysis_tasks 等表结构纳入版本控制。

替代方案是继续自动建表。它适合 demo，但不适合从 MySQL 切换到 PostgreSQL 后的团队开发和验收环境。

### 以 `training_sessions` 作为业务中心

训练记录代表一次测试或训练，是运动员、视频、分析结果和报告之间的业务聚合根。`analysis_tasks` 改为引用 `session_id`，模型请求由后端根据 session 聚合运动员信息、训练上下文和绑定视频生成。

替代方案是继续以 `video_files` 作为中心。它无法自然表达多机位、同步偏移、同一次训练的多个资源以及 session 级报告。

### 分离 `video_files` 和 `session_videos`

`video_files` 只记录文件存储事实，例如原始文件名、存储路径、MIME type、大小和 checksum。`session_videos` 记录业务关系，例如 `session_id`、`video_file_id`、`view_type`、`fps`、`resolution` 和 `sync_offset_ms`。

替代方案是把 `session_id` 和 `view_type` 直接塞进 `video_files`。这会把文件存储层和训练业务层混在一起，后续多机位和对象存储迁移都会更难。

### 先用 JWT Bearer token 完成平台认证

第一版认证只需要支持教练注册、登录和读取当前用户。密码使用 bcrypt 哈希，token 使用 JWT，受保护接口通过 `get_current_user` 获取当前登录用户。

替代方案是 session cookie 或第三方 OAuth。它们适合更完整的生产登录，但超出当前平台核心骨架需求。

### 报告 API 面向 `session_id`

报告的展示对象是一次训练记录，而不是孤立任务。`POST /api/v1/reports/generate` 接收 `session_id`，`GET /api/v1/reports/{session_id}` 返回该训练记录最新或唯一可用报告。

替代方案是保留 `GET /reports/{task_id}`。它对现有代码改动更小，但会让前端在“训练记录详情”和“报告页”之间携带任务细节，削弱 session 作为业务中心的清晰度。

## Risks / Trade-offs

- PostgreSQL 切换导致本地环境无法连接 → 提供 `docker-compose.yml`、`.env.example` 和清晰启动顺序，并在验收中包含数据库连接检查。
- Alembic 初始接入可能漏导入模型 → 在 `models/__init__.py` 汇总导出所有模型，并在 `alembic/env.py` 显式加载模型包。
- 从 `video_id` 到 `session_id` 的 API 迁移会影响现有前端调用 → 保持第一版接口清单稳定，并把旧 `/tasks` 流程作为迁移对象处理。
- BackgroundTasks 在进程重启时不可靠 → 本次仍保留 MVP 后台执行，但任务状态必须持久化；后续可平滑迁移到 Celery + Redis。
- 模型服务暂时可能只支持单视频 payload → 后端生成 session 级 payload 时允许视频数组只有一个元素，并保留 `schema_version` 以便模型服务逐步升级。

## Migration Plan

1. 添加 PostgreSQL 依赖、配置项、`.env.example` 和本地 Docker Compose。
2. 初始化 Alembic，移除应用启动时正式建表逻辑。
3. 拆分模型和 schema 文件，加入平台核心表并生成初始 migration。
4. 新增认证、运动员、训练记录和 session 视频绑定 API。
5. 将现有 tasks 路由和 service 迁移为 analysis 路由与 session 级任务。
6. 调整模型服务请求 payload、结果保存和报告生成，使它们引用 `session_id`。
7. 用 Swagger 或 API 测试跑通注册、登录、创建运动员、创建训练记录、上传视频、绑定视频、提交分析、查询状态和读取报告。

回滚策略：如果 PostgreSQL/Alembic 接入阻塞，可暂时保留旧 `videos` 上传接口和本地文件存储，但不应继续扩展旧 `video_id` 级任务模型。

## Open Questions

- 第一版是否需要 `PUT /api/v1/athletes/{athlete_id}` 和 `PUT /api/v1/sessions/{session_id}`，还是只覆盖创建与读取验收链路。
- 模型服务在本次是否同步升级为接收 `videos[]`，还是由后端在一段时间内兼容单视频请求。
- `POST /api/v1/analysis/{task_id}/result` 是否需要内部服务 token 或签名校验，还是先作为本地开发回调接口。
