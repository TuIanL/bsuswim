## 1. PostgreSQL 与本地环境

- [x] 1.1 将后端数据库默认连接串从 MySQL 改为 `postgresql+psycopg`
- [x] 1.2 更新后端依赖，移除 MySQL 驱动并加入 PostgreSQL、JWT、密码哈希和 Alembic 相关依赖
- [x] 1.3 新增或更新 `.env.example`，包含 PostgreSQL、JWT、CORS、上传目录和模型服务配置
- [x] 1.4 新增本地 `docker-compose.yml`，提供 PostgreSQL，并保留 Redis 和 MinIO 扩展服务
- [x] 1.5 确认后端配置能读取环境变量并覆盖默认值

## 2. Alembic 与模型结构

- [x] 2.1 初始化 Alembic 配置并让 migration 使用应用的 SQLAlchemy `Base`
- [x] 2.2 移除应用启动时对正式表结构的 `Base.metadata.create_all` 依赖
- [x] 2.3 将 `backend/app/models.py` 拆分为按领域组织的 `models/` 包
- [x] 2.4 将 `backend/app/schemas.py` 拆分为按领域组织的 `schemas/` 包
- [x] 2.5 新增 `User`、`Team`、`Athlete`、`TrainingSession`、`SessionVideo` 等平台核心模型
- [x] 2.6 调整 `AnalysisTask` 从 `video_id` 关联迁移为 `session_id` 关联
- [x] 2.7 生成并检查 PostgreSQL 初始 migration，确保核心表、索引、外键和枚举可创建

## 3. 认证与用户接口

- [x] 3.1 新增密码哈希、密码验证和 JWT access token 生成工具
- [x] 3.2 新增当前用户依赖，支持从 Bearer token 解析并加载用户
- [x] 3.3 实现 `POST /api/v1/auth/register`
- [x] 3.4 实现 `POST /api/v1/auth/login`
- [x] 3.5 实现 `GET /api/v1/users/me`
- [x] 3.6 为受保护接口接入当前用户上下文

## 4. 运动员、训练记录与视频绑定

- [x] 4.1 实现 `POST /api/v1/athletes`
- [x] 4.2 实现 `GET /api/v1/athletes`
- [x] 4.3 实现 `GET /api/v1/athletes/{athlete_id}`
- [x] 4.4 实现 `GET /api/v1/athletes/{athlete_id}/sessions`
- [x] 4.5 实现 `POST /api/v1/sessions`
- [x] 4.6 实现 `GET /api/v1/sessions`
- [x] 4.7 实现 `GET /api/v1/sessions/{session_id}`
- [x] 4.8 将视频上传接口规范为 `POST /api/v1/videos/upload`
- [x] 4.9 实现 `GET /api/v1/videos/{video_id}`
- [x] 4.10 实现 `POST /api/v1/sessions/{session_id}/videos`
- [x] 4.11 实现 `GET /api/v1/sessions/{session_id}/videos`

## 5. Session 级分析与报告

- [x] 5.1 将旧 `tasks` 路由迁移为 `analysis` 路由
- [x] 5.2 实现 `POST /api/v1/analysis/submit`，基于 `session_id` 创建分析任务
- [x] 5.3 实现 `GET /api/v1/analysis/{task_id}/status`
- [x] 5.4 实现 `GET /api/v1/analysis/{task_id}/result`
- [x] 5.5 实现 `POST /api/v1/analysis/{task_id}/result`
- [x] 5.6 将模型服务请求升级为包含 `task_id`、`session_id`、运动员、训练记录和 `videos[]`
- [x] 5.7 调整分析结果保存逻辑，确保结果、任务状态和错误信息都围绕 session 级任务更新
- [x] 5.8 实现 `POST /api/v1/reports/generate`
- [x] 5.9 实现 `GET /api/v1/reports/{session_id}`
- [x] 5.10 调整报告构建逻辑，使报告包含运动员、训练记录、分析任务和结果来源信息

## 6. 验证与兼容收尾

- [x] 6.1 使用 migration 在空 PostgreSQL 数据库上创建全部表
- [x] 6.2 用 Swagger 或 API 测试跑通注册、登录、读取当前用户
- [x] 6.3 跑通创建运动员、创建训练记录、上传视频和绑定 session 视频
- [x] 6.4 跑通提交 session 级分析、查询状态、保存或模拟结果、读取结果
- [x] 6.5 跑通生成并读取 session 级报告
- [x] 6.6 更新后端 README 或开发说明中的本地启动流程和 API 入口
- [x] 6.7 运行后端测试或至少执行导入检查、migration 检查和 FastAPI 启动检查
