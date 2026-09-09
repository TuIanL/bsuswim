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
VIDEO_UPLOAD_MAX_BYTES='524288000'
ANNOTATION_UPLOAD_MAX_BYTES='52428800'
JWT_SECRET_KEY='please-change-this-secret'
```

AI 报告解读默认关闭。只做本地确定性联调时可使用 fake provider，不会发起外部请求：

```bash
AI_INTERPRETATION_ENABLED=true
AI_INTERPRETATION_V3_ENABLED=true
AI_INTERPRETATION_AUTO_GENERATE=true
AI_INTERPRETATION_PROVIDER=fake
AI_INTERPRETATION_MODEL=deterministic-test
```

接入 DeepSeek 时使用 `provider=deepseek`、base URL `https://api.deepseek.com` 和
模型 `deepseek-v4-flash`，然后在本机设置 `AI_INTERPRETATION_API_KEY`。其他支持
OpenAI 严格 JSON Schema 的服务仍可使用 `provider=openai_compatible`。完整预算、隐私与试运行约定见
[`ai-report-interpretation-operations.md`](./ai-report-interpretation-operations.md)。

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

## 测试命令

以下命令均可从仓库根目录执行；后端 pytest 不依赖先进入 `backend/`：

```bash
# 快速质量检查
python -m pytest -q --tb=short
cd frontend-vue && npm test -- --run && npm run build
cd .. && openspec validate --specs --strict --json

# Golden fixture contract（需要本地 fixture）
python -m pytest -q backend/tests/golden -m golden_contract

# 完整浏览器/PDF E2E（需要 PostgreSQL、Chromium、FFmpeg 和完整 fixture）
GOLDEN_E2E_ENABLED=1 \
GOLDEN_E2E_BACKEND_URL=http://127.0.0.1:8001 \
GOLDEN_E2E_FRONTEND_URL=http://127.0.0.1:5174 \
PDF_RENDER_BASE_URL=http://127.0.0.1:5174 \
BACKEND_PUBLIC_BASE_URL=http://127.0.0.1:8001 \
python -m pytest -q backend/tests/e2e -m golden_e2e
```

Golden fixture 缺失或校验和不匹配时测试会直接失败，不会自动回退到 synthetic 数据。当前视频采用约 20MB 的仓库内压缩 fixture，保持原始分辨率、帧率和帧数，方便开发环境与 CI 直接使用；生产级文件鉴权和私有对象存储另行处理。
完整 E2E 会创建临时教练、运动员和训练记录，通过真实 HTTP 上传并绑定视频、ingest CVAT XML、提交 `annotation_kinematics` pipeline，最后由真实 Playwright/Chromium 打开前端 print route 并生成 PDF。失败日志使用 `E2E_INFRA_ERROR:<code>` 区分服务/fixture/浏览器环境问题，使用 `E2E_PRODUCT_ASSERTION:<code>` 标识产品契约失败；未配置 `GOLDEN_E2E_ENABLED=1` 时会明确失败，不会静默跳过。
GitHub Actions 的 `.github/workflows/golden-e2e.yml` 只在手动触发或定时任务中运行完整检查，普通 PR 不上传任何私有 fixture 凭证；仓库内 fixture 缺失、损坏或服务未启动时均会失败并输出稳定错误标识。`expected/` 仍是待显式批准的候选契约，不会被普通测试自动改写。
