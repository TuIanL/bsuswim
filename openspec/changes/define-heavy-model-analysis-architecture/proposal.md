## Why

当前项目已经有游泳分析平台的前端原型和交互规格，但尚未固化后端、数据库、文件存储、重模型服务和异步分析链路的技术架构。由于后续会接入类似 YOLO 的重模型，模型运行环境、GPU 资源、视频处理耗时和任务状态管理都需要从业务后端中解耦出来，避免早期实现把平台绑死在单进程或同步请求模式里。

## What Changes

- 确定平台技术栈：前端采用 Vue3、TypeScript、Vite、Element Plus、ECharts、Pinia、Axios；后端采用 FastAPI、Pydantic、SQLAlchemy、MySQL。
- 引入独立 FastAPI 模型服务，承载 YOLO 类目标检测、姿态/动作分析、视频抽帧和指标计算等重计算流程。
- 建立视频上传、文件落盘、分析任务入库、异步调用模型服务、结果保存、报告展示的端到端架构约束。
- 明确本地 `uploads` 作为 MVP 文件存储方案，后期可迁移到 MinIO；异步任务先用 FastAPI `BackgroundTasks`，后期可迁移到 Celery + Redis。
- 明确报告先以 HTML 报告页交付，后期再增加 PDF 导出能力。
- 为后续实现创建可验收的能力规格和任务拆解。

## Capabilities

### New Capabilities

- `heavy-model-analysis-architecture`: 约束重模型游泳视频分析平台的前后端技术栈、文件存储、模型服务隔离、异步任务状态和报告生成链路。

### Modified Capabilities

- `swim-video-analysis-job-flow`: 分析任务流需要从前端演示状态扩展为真实后端任务状态、模型服务调用状态和错误恢复状态。
- `swim-visual-analysis-workspace`: 可视化工作台需要支持真实分析结果，包括视频引用、骨架点、检测框、关键指标和时间轴数据。
- `swim-interactive-performance-report`: 报告能力需要支持从后端分析结果生成 HTML 报告页，并为后期 PDF 导出预留边界。

## Impact

- 前端应用架构将从现有原型过渡到 Vue3 + TypeScript + Vite 的分析平台实现，包含路由、状态管理、API client、视频播放、Canvas 叠加和 ECharts 图表。
- 业务后端新增 FastAPI 应用、Pydantic schemas、SQLAlchemy models、MySQL 连接、上传文件管理、分析任务 API 和报告 API。
- 模型服务新增独立 FastAPI 应用，允许单独安装 YOLO 类模型、深度学习框架、视频处理依赖，并可独立部署到 GPU 环境。
- 数据库需要保存视频、分析任务、分析结果、报告元数据和文件路径/对象键。
- 本地开发和部署需要同时管理前端、业务后端、模型服务、MySQL 和本地 `uploads` 目录。
