## ADDED Requirements

### Requirement: 前端 SHALL 展示运动学可视化 artifacts

系统 SHALL 在前端展示从后端生成的运动学可视化 artifacts，包括关键帧图片、图表、雷达图等。

#### Scenario: 分析完成后自动获取 artifacts

- **WHEN** 指标数据计算完成
- **AND** 存在对应的 `annotation_metric_id`
- **THEN** 系统 SHALL 自动调用 `generateKinematicArtifacts` API 生成 artifacts
- **AND** SHALL 轮询 `getKinematicArtifacts` API 直到生成完成

#### Scenario: artifacts 数据展示

- **WHEN** artifacts 数据加载完成
- **THEN** 系统 SHALL 在工作流页面显示可视化面板
- **AND** SHALL 展示关键帧图片（带标注的视频帧）
- **AND** SHALL 展示图表（身体角度、轨迹等）
- **AND** SHALL 展示雷达图（多维度指标对比）

#### Scenario: artifacts 生成中状态

- **WHEN** artifacts 正在生成中
- **THEN** 系统 SHALL 显示加载状态和进度
- **AND** SHALL 显示预计剩余时间（如果可用）

#### Scenario: artifacts 生成失败

- **WHEN** artifacts 生成失败
- **THEN** 系统 SHALL 显示错误信息
- **AND** SHALL 提供重新生成按钮

### Requirement: 前端 SHALL 支持 artifacts 的强制重新生成

系统 SHALL 支持用户强制重新生成 artifacts，覆盖已有的生成结果。

#### Scenario: 用户触发重新生成

- **WHEN** 用户在可视化面板点击"重新生成"按钮
- **THEN** 系统 SHALL 调用 `generateKinematicArtifacts` API 并设置 `force=true`
- **AND** SHALL 重新开始生成流程
