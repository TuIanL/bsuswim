# 智泳云枢

智泳云枢是一个面向竞技游泳训练场景的 AI 视频分析平台。项目目标不是只做单点姿态识别，而是把视频上传、模型分析、任务管理、可视化工作台和训练报告串成一条完整链路，服务教练复盘、运动员技术评估和后续训练建议生成。

当前仓库同时包含三类内容：

- Web 分析平台：前端、业务后端、模型服务
- AI 算法实验基础：MMPose / YOLO 方向的本地环境、数据目录、权重目录
- 规格与设计文档：OpenSpec 变更记录和 `docs/` 沉淀文档

## 项目定位

- 面向对象：游泳教练、运动员、科研或训练分析团队
- 核心输入：训练视频、泳姿与采集元数据
- 核心输出：检测框、关键点、动作阶段、技术指标、诊断结论、HTML 报告
- 当前阶段：MVP 架构已搭起，模型服务先以 stub 结果跑通链路，后续接入真实 YOLO / MMPose 推理

## 技术栈

### 前端

- Vue3
- TypeScript
- Vite
- Element Plus
- ECharts
- Pinia
- Axios
- 原生 `video`
- Canvas

### 后端

- FastAPI
- Pydantic
- SQLAlchemy
- PostgreSQL
- Alembic
- FastAPI `BackgroundTasks`

### 模型服务

- FastAPI 独立服务
- 后续接入 YOLO / MMPose / OpenCV / FFmpeg / PyTorch

### 文件与报告

- 本地 `uploads/` 起步
- 后期可迁移 MinIO
- HTML 报告页优先
- 后期补 PDF 导出

## 仓库结构

```text
backend/         业务后端 FastAPI
frontend/        早期 Next/React 原型
frontend-vue/    正式 Vue3 分析平台
model_service/   独立模型服务
docs/            项目文档
data/            训练与标注数据目录
weights/         模型权重目录
outputs/         输出结果目录
uploads/         本地上传视频目录
openspec/        规格、提案、归档变更
```

## 启动方式

### 1. Python 环境

项目使用仓库内的 conda 环境：

```bash
conda activate /Users/tuian/Documents/大学/竞赛/大创/游泳/swim/.conda/swim-pose
```

不要把依赖装到全局或 base 环境里。

### 2. 启动模型服务

```bash
cd model_service
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8100
```

### 3. 启动业务后端

先启动本地依赖：

```bash
docker compose up -d postgres redis minio
```

默认环境变量可参考 `.env.example`：

```bash
export DATABASE_URL='postgresql+psycopg://swim:swim@localhost:5432/swim_analysis'
export MODEL_SERVICE_URL='http://127.0.0.1:8100'
export UPLOAD_DIR='uploads'
export JWT_SECRET_KEY='please-change-this-secret'
```

启动并迁移数据库：

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### 4. 启动 Vue 前端

```bash
cd frontend-vue
npm install
VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

如果不设置 `VITE_API_BASE_URL`，前端会进入 demo 数据模式。

### 5. 访问地址

- Vue 前端：`http://127.0.0.1:5173`
- 业务后端：`http://127.0.0.1:8000`
- 模型服务：`http://127.0.0.1:8100`

## 本地 AI 实验基础

当前本地环境已验证的核心版本：

```text
Python 3.10.20
PyTorch 2.12.0
NumPy 1.26.4
OpenCV 4.11.0
MMEngine 0.10.7
MMCV Lite 2.1.0
MMDetection 3.3.0
MMPose 1.3.2
```

数据目录约定：

```text
data/swim_coco/annotations/train.json
data/swim_coco/annotations/val.json
data/swim_coco/images/train/
data/swim_coco/images/val/
```

权重放在 `weights/`，推理输出或导出视频放在 `outputs/`。

## 文档导航

- [技术栈与架构说明](/Users/tuian/Documents/大学/竞赛/大创/游泳/swim/docs/tech-stack.md)
- [数据库设计](/Users/tuian/Documents/大学/竞赛/大创/游泳/swim/docs/database-design.md)
- [AI 接口规范](/Users/tuian/Documents/大学/竞赛/大创/游泳/swim/docs/ai-api-spec.md)
- [本地开发说明](/Users/tuian/Documents/大学/竞赛/大创/游泳/swim/docs/local-development.md)
- [后期升级边界](/Users/tuian/Documents/大学/竞赛/大创/游泳/swim/docs/upgrade-paths.md)
