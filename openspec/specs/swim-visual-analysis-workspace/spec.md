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
- **THEN** 工作台 MUST 从后端加载视频资源引用、任务元数据、检测结果、关键点或骨架数据、阶段标签和指标摘要

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
- **THEN** 主视频区域 MUST 使用后端授权或公开的播放 URL 展示原始视频

#### Scenario: Video source cannot be loaded
- **WHEN** 视频文件缺失、URL 失效或后端返回不可访问
- **THEN** 工作台 MUST 显示稳定错误状态，并保留任务元数据和返回任务管理的操作
