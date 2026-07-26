## ADDED Requirements

### Requirement: One-click startup script launches both frontend and backend

系统 SHALL 提供 `start-web.command` 脚本，一键启动前端 Vite dev server 和后端 FastAPI uvicorn 进程。

#### Scenario: Script starts both services

- **WHEN** 用户执行 `start-web.command`
- **THEN** 脚本 SHALL 启动 FastAPI 后端（`uvicorn app.main:app --host 127.0.0.1 --port 8000`）
- **AND** 脚本 SHALL 启动 Vue/Vite 前端 dev server（端口 5174）
- **AND** 两个进程的 PID SHALL 记录到 `.web-dev.pid` 供 `stop-web.command` 清理

#### Scenario: Backend database is checked before startup

- **WHEN** 脚本检测到 Docker 正在运行
- **THEN** 脚本 SHALL 确保 postgres 容器已启动
- **AND** 脚本 SHALL 等待数据库就绪（最多 10 秒）
- **AND** 脚本 SHALL 执行 alembic upgrade head 确保 migration 最新

#### Scenario: Frontend waits for backend readiness

- **WHEN** 前端 Vite dev server 启动
- **THEN** 脚本 SHALL 在后端 health check 通过后才启动前端
- **AND** 前端 SHALL 配置 `VITE_API_BASE_URL=http://127.0.0.1:8000` 以连接后端

### Requirement: Stop script cleans up all processes

系统 SHALL 提供 `stop-web.command` 脚本，同时停止前端和后端进程。

#### Scenario: Stop script terminates all managed processes

- **WHEN** 用户执行 `stop-web.command`
- **THEN** 脚本 SHALL 终止 PID 文件中记录的所有进程
- **AND** 脚本 SHALL 清理 PID 文件
