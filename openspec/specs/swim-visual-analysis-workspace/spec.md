# swim-visual-analysis-workspace Specification

## Purpose
TBD - created by archiving change port-pickleball-platform-to-swim-analysis. Update Purpose after archive.
## Requirements
### Requirement: Video-first swim workspace
The system SHALL provide a swim visual-analysis workspace centered on side-view video review and analysis status.

#### Scenario: User opens demo visual analysis
- **WHEN** the user opens the swim visual workspace without a real job context
- **THEN** the system renders a demo swim analysis experience with a large video-style area, swim session context, and clear demo/source indication

#### Scenario: User opens job-specific visual analysis
- **WHEN** the user opens the visual workspace for a completed swim analysis job
- **THEN** the system renders job metadata, source clarity, available result actions, and the video or demo visual area for that job

### Requirement: Swim-specific visual overlays
The visual workspace SHALL use swim-analysis overlays rather than court or rally overlays.

#### Scenario: User views the demo overlay layer
- **WHEN** the swim demo workspace is visible
- **THEN** the visual area shows swim-specific cues such as lane direction, above-water and underwater capture labels, stitched side-view indicators, keypoint traces, body-angle markers, stroke-phase markers, rhythm ticks, and symmetry cues

#### Scenario: User reads overlay labels
- **WHEN** overlay labels are shown
- **THEN** labels explain swim posture, body line, stroke rhythm, breathing timing, kick consistency, or coach-review context instead of pickleball actions

### Requirement: Layer availability states
The workspace SHALL distinguish available, loading, unavailable, and demo visual layers.

#### Scenario: Keypoint layer is unavailable
- **WHEN** keypoint data is not available for a job
- **THEN** the workspace keeps the base video or demo visual usable and labels the keypoint layer as unavailable without showing unrelated placeholder detections as real output

#### Scenario: Demo overlays are shown
- **WHEN** the workspace renders sample visual layers
- **THEN** the system labels them as demo or simulated content

### Requirement: Workspace result actions
The visual workspace SHALL provide compact navigation to lower-level swim analysis results.

#### Scenario: User reviews completed visual analysis
- **WHEN** a completed swim analysis result is visible
- **THEN** the workspace exposes actions for report review, posture diagnosis, rhythm metrics, training suggestions, and task management

#### Scenario: User selects a result action
- **WHEN** the user selects a result or report action
- **THEN** the system navigates to the corresponding job-aware report or training view without losing the job context

### Requirement: Responsive video workspace
The workspace SHALL keep the primary visual analysis area usable on desktop and mobile.

#### Scenario: User views workspace on desktop
- **WHEN** the viewport is wide enough for a two-column layout
- **THEN** the video area remains dominant and the status or action rail appears adjacent to it

#### Scenario: User views workspace on mobile
- **WHEN** the viewport is narrow
- **THEN** the video area, layer controls, metadata, and result actions stack without overlapping text or controls

### Requirement: Real analysis result rendering
可视化工作台 SHALL 渲染后端保存的真实模型分析结果。

#### Scenario: User opens completed backend job
- **WHEN** 用户打开状态为 `completed` 的真实分析任务
- **THEN** 工作台 MUST 从后端加载训练记录上下文、运动员信息、绑定视频资源引用、检测结果、关键点或骨架数据、阶段标签和指标摘要

#### Scenario: Result schema version is unsupported
- **WHEN** 后端返回的分析结果 `schema_version` 不受当前前端支持
- **THEN** 工作台 MUST 显示结果不可用或需升级的状态，而不是把未知结构渲染为真实分析

### Requirement: Canvas overlay synchronization
可视化工作台 SHALL 使用 Canvas 将模型结果与视频时间轴同步叠加。

#### Scenario: User plays analyzed video
- **WHEN** 视频播放到某个时间点
- **THEN** Canvas 叠加层 MUST 根据视频 `currentTime` 匹配对应帧或时间戳的检测框、关键点、骨架线、角度线和阶段提示

#### Scenario: Overlay data is missing for current time
- **WHEN** 当前视频时间点没有可用模型输出
- **THEN** 工作台 MUST 保持视频播放可用，并将对应图层标记为 unavailable 或 limited

### Requirement: Backend video source handling
可视化工作台 SHALL 使用后端提供的视频访问 URL 或资源引用播放真实视频。

#### Scenario: Backend provides playable video URL
- **WHEN** 工作台加载真实分析任务
- **THEN** 主视频区域 MUST 使用后端通过 session 视频关系提供的授权或公开播放 URL 展示原始视频

#### Scenario: Video source cannot be loaded
- **WHEN** 视频文件缺失、URL 失效或后端返回不可访问
- **THEN** 工作台 MUST 显示稳定错误状态，并保留任务元数据和返回任务管理的操作

### Requirement: Session video selection in workspace
可视化工作台 SHALL 能够处理一个训练记录下的一个或多个绑定视频。

#### Scenario: Completed task has multiple bound videos
- **WHEN** 工作台加载的训练记录包含多个机位视频
- **THEN** 系统 MUST 展示可选择或可识别的机位信息，并保持当前可播放视频与分析结果上下文一致

#### Scenario: Completed task has one bound video
- **WHEN** 工作台加载的训练记录只包含一个视频
- **THEN** 系统 MUST 将该视频作为默认主视频展示，并保留机位来源标识

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

