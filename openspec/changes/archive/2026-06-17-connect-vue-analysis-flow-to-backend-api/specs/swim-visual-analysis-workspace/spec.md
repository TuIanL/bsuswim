## ADDED Requirements

### Requirement: Backend task workspace loading
真实后端模式下，视觉工作台 SHALL 基于分析任务 ID 加载任务状态、分析结果和训练记录视频资源。

#### Scenario: User opens workspace for backend task
- **WHEN** 用户打开 `/workspace/{task_id}` 且前端配置了后端 API
- **THEN** 工作台 MUST 从后端加载该任务的状态、`session_id`、分析结果和训练记录绑定视频摘要

#### Scenario: Workspace opens before task completion
- **WHEN** 用户打开尚未完成的真实分析任务工作台
- **THEN** 工作台 MUST 展示任务当前阶段和进度，继续轮询状态，并在结果尚不可用时不渲染真实叠加层

#### Scenario: Workspace opens after task completion
- **WHEN** 后端任务状态为 `completed` 且分析结果存在
- **THEN** 工作台 MUST 渲染任务指标、结果 schema、可用视频播放 URL 和进入 session 报告页的操作

### Requirement: Workspace uses session video sources
真实后端工作台 SHALL 使用训练记录视频绑定关系提供的资源作为视频来源。

#### Scenario: Session has bound videos
- **WHEN** 工作台加载到该任务所属训练记录的一个或多个绑定视频
- **THEN** 工作台 MUST 选择一个默认主视频用于播放，并展示或保留其机位类型、文件名和播放 URL

#### Scenario: Video source is missing
- **WHEN** 后端任务存在但训练记录没有可播放视频 URL 或视频加载失败
- **THEN** 工作台 MUST 展示稳定错误或受限状态，并保留任务状态、指标和返回任务管理的操作

### Requirement: Workspace does not call legacy task workspace API
真实后端模式下，视觉工作台 SHALL 不依赖旧 `/api/v1/tasks/{task_id}/workspace`。

#### Scenario: Backend mode workspace data is requested
- **WHEN** 前端需要加载真实任务工作台数据
- **THEN** 前端 MUST 使用 `/api/v1/analysis/{task_id}/status`、`/api/v1/analysis/{task_id}/result`、session 视频 API 或后端提供的正式 analysis workspace 聚合 API
