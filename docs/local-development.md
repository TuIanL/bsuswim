# 本地开发说明

本仓库唯一正式 Web 应用为 `frontend-vue/`，所有前端开发、构建和预览命令均在该目录下执行。

## 服务划分

- `frontend-vue/`: Vue3 + TypeScript + Vite + Element Plus + ECharts + Pinia + Axios（唯一正式前端）
- `backend/`: FastAPI 业务后端，负责认证、运动员、训练记录、上传、分析、结果、报告和模型服务调度
- `model_service/`: 独立 FastAPI 模型服务，MVP 使用 stub runtime，后期替换为 YOLO/MMPose 推理
- `uploads/`: MVP 本地视频存储目录

## 环境变量

业务后端默认使用 PostgreSQL:

```bash
DATABASE_URL='postgresql+psycopg://swim:swim@localhost:5432/swim_analysis'
MODEL_SERVICE_URL='http://127.0.0.1:8100'
UPLOAD_DIR='uploads'
JWT_SECRET_KEY='please-change-this-secret'
```

前端连接业务后端:

```bash
VITE_API_BASE_URL='http://127.0.0.1:8000'
```

不设置 `VITE_API_BASE_URL` 时，Vue 前端会进入 demo 数据模式。

## 启动顺序

```bash
# 1. 启动本地依赖
docker compose up -d postgres redis minio

# 2. 启动模型服务
cd model_service
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8100

# 3. 启动业务后端
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# 4. 启动 Vue 前端
cd frontend-vue
npm install
VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

业务后端数据库表通过 Alembic 管理；修改模型后应生成新的 migration，再执行 `alembic upgrade head`。
