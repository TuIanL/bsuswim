# 本地开发说明

本项目保留现有 `frontend/` Next/React 原型作为交互参考，正式分析平台从 `frontend-vue/` 起步。

## 服务划分

- `frontend-vue/`: Vue3 + TypeScript + Vite + Element Plus + ECharts + Pinia + Axios
- `backend/`: FastAPI 业务后端，负责上传、任务、结果、报告和模型服务调度
- `model_service/`: 独立 FastAPI 模型服务，MVP 使用 stub runtime，后期替换为 YOLO/MMPose 推理
- `uploads/`: MVP 本地视频存储目录

## 环境变量

业务后端默认使用 MySQL:

```bash
DATABASE_URL='mysql+pymysql://swim:swim@127.0.0.1:3306/swim_analysis?charset=utf8mb4'
MODEL_SERVICE_URL='http://127.0.0.1:8100'
UPLOAD_DIR='uploads'
```

前端连接业务后端:

```bash
VITE_API_BASE_URL='http://127.0.0.1:8000'
```

不设置 `VITE_API_BASE_URL` 时，Vue 前端会进入 demo 数据模式。

## 启动顺序

```bash
# 1. 启动模型服务
cd model_service
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8100

# 2. 启动业务后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 3. 启动 Vue 前端
cd frontend-vue
npm install
VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

业务后端启动时会通过 SQLAlchemy 创建当前 MVP 需要的数据表。正式环境建议迁移到 Alembic 管理数据库版本。
