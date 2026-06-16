## 1. 项目结构与技术栈初始化

- [x] 1.1 确认现有 Next/React 原型的保留方式，并创建 Vue3 + TypeScript + Vite 前端应用目录
- [x] 1.2 安装并配置 Element Plus、ECharts、Pinia、Axios、路由和基础样式入口
- [x] 1.3 创建业务后端 FastAPI 项目结构，区分 API routes、schemas、models、services、database 和 settings
- [x] 1.4 创建独立模型服务 FastAPI 项目结构，区分 inference API、model runtime、video processing 和 result schemas
- [x] 1.5 准备本地开发配置，覆盖前端、业务后端、模型服务、MySQL 和 `uploads` 目录

## 2. 数据库与后端基础能力

- [x] 2.1 配置 SQLAlchemy、MySQL 连接和数据库 session 生命周期
- [x] 2.2 定义视频文件、分析任务、分析结果和报告元数据的数据模型
- [x] 2.3 定义 Pydantic schemas，覆盖上传响应、任务创建、任务状态、模型结果和报告数据
- [x] 2.4 实现本地 `uploads` 存储服务，保存文件路径、原始文件名、大小、MIME type 和上传时间
- [x] 2.5 实现视频上传 API，并创建对应的视频记录

## 3. 分析任务与异步调度

- [x] 3.1 实现分析任务创建 API，接收视频引用和游泳训练元数据
- [x] 3.2 实现任务状态机，覆盖 `uploaded`、`queued`、`processing`、`result_saving`、`completed` 和 `failed`
- [x] 3.3 使用 FastAPI `BackgroundTasks` 启动 MVP 异步分析流程
- [x] 3.4 实现任务列表、任务详情和任务状态查询 API
- [x] 3.5 实现失败处理，保存模型服务错误、超时错误、结果校验错误和用户可读错误原因

## 4. 模型服务集成

- [x] 4.1 在模型服务中定义分析请求和结构化分析响应 schema，包含 `schema_version`
- [x] 4.2 实现模型服务健康检查 API 和 stub 分析 API，用固定样例结果跑通链路
- [x] 4.3 在业务后端实现模型服务 client，支持超时、错误映射和响应校验
- [x] 4.4 将模型服务返回的检测框、关键点、阶段标签、指标和诊断线索保存为分析结果
- [x] 4.5 预留 YOLO 类模型加载、视频抽帧、推理和指标计算的 runtime 接口

## 5. Vue 前端任务流

- [x] 5.1 实现 Axios API client，封装上传、创建任务、查询任务、获取结果和获取报告
- [x] 5.2 实现视频上传与训练元数据表单，使用 Element Plus 完成校验和提交状态
- [x] 5.3 实现任务管理视图，从后端加载任务列表并展示状态、进度、更新时间和可用操作
- [x] 5.4 实现任务详情或处理中视图，支持轮询后端任务状态
- [x] 5.5 保留 demo 数据模式，并在无后端配置时不阻塞前端展示

## 6. 可视化工作台

- [x] 6.1 实现真实任务的工作台数据加载，读取视频 URL、任务元数据和分析结果
- [x] 6.2 使用原生 `video` 播放后端提供的视频资源
- [x] 6.3 使用 Canvas 绘制检测框、关键点、骨架线、角度线、阶段提示和轨迹层
- [x] 6.4 根据视频 `currentTime` 同步当前帧或时间戳对应的模型输出
- [x] 6.5 实现图层 unavailable、limited、loading 和 schema 不兼容状态

## 7. HTML 报告页

- [x] 7.1 实现报告数据 API，基于分析结果生成摘要、指标、诊断和训练建议
- [x] 7.2 实现 Vue HTML 报告页，展示训练摘要、关键指标、ECharts 图表、诊断证据和建议
- [x] 7.3 在报告中标记数据来源、分析任务 ID、报告生成时间和 demo/真实数据状态
- [x] 7.4 将 PDF 导出入口标记为暂不可用或隐藏，避免暗示已实现能力

## 8. 验证与升级边界

- [x] 8.1 验证上传视频后能创建任务、进入队列、调用 stub 模型服务并完成结果保存
- [x] 8.2 验证前端刷新后仍能从后端恢复任务列表、任务状态、工作台和报告
- [x] 8.3 验证模型服务失败、结果 schema 不兼容、视频资源缺失时前端显示稳定错误状态
- [x] 8.4 记录从本地 `uploads` 迁移到 MinIO 时需要替换的存储接口和配置项
- [x] 8.5 记录从 `BackgroundTasks` 迁移到 Celery + Redis 时需要替换的调度接口和保持不变的任务 API 契约
