## ADDED Requirements

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
