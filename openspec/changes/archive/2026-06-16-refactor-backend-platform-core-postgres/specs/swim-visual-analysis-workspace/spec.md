## MODIFIED Requirements

### Requirement: Real analysis result rendering
可视化工作台 SHALL 渲染后端保存的真实模型分析结果。

#### Scenario: User opens completed backend job
- **WHEN** 用户打开状态为 `completed` 的真实分析任务
- **THEN** 工作台 MUST 从后端加载训练记录上下文、运动员信息、绑定视频资源引用、检测结果、关键点或骨架数据、阶段标签和指标摘要

#### Scenario: Result schema version is unsupported
- **WHEN** 后端返回的分析结果 `schema_version` 不受当前前端支持
- **THEN** 工作台 MUST 显示结果不可用或需升级的状态，而不是把未知结构渲染为真实分析

### Requirement: Backend video source handling
可视化工作台 SHALL 使用后端提供的视频访问 URL 或资源引用播放真实视频。

#### Scenario: Backend provides playable video URL
- **WHEN** 工作台加载真实分析任务
- **THEN** 主视频区域 MUST 使用后端通过 session 视频关系提供的授权或公开播放 URL 展示原始视频

#### Scenario: Video source cannot be loaded
- **WHEN** 视频文件缺失、URL 失效或后端返回不可访问
- **THEN** 工作台 MUST 显示稳定错误状态，并保留任务元数据和返回任务管理的操作

## ADDED Requirements

### Requirement: Session video selection in workspace
可视化工作台 SHALL 能够处理一个训练记录下的一个或多个绑定视频。

#### Scenario: Completed task has multiple bound videos
- **WHEN** 工作台加载的训练记录包含多个机位视频
- **THEN** 系统 MUST 展示可选择或可识别的机位信息，并保持当前可播放视频与分析结果上下文一致

#### Scenario: Completed task has one bound video
- **WHEN** 工作台加载的训练记录只包含一个视频
- **THEN** 系统 MUST 将该视频作为默认主视频展示，并保留机位来源标识
