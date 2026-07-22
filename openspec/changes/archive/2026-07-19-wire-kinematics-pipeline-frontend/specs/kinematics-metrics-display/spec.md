## ADDED Requirements

### Requirement: 前端 SHALL 展示运动学指标数据

系统 SHALL 在前端展示从后端计算的运动学指标数据，包括身体姿态、上肢、下肢等维度的指标。

#### Scenario: 分析完成后自动获取指标数据

- **WHEN** 分析任务状态变为 `completed`
- **AND** 存在对应的 `normalized_annotation_id`
- **THEN** 系统 SHALL 自动调用 `calculateMetrics` API 获取指标数据
- **AND** SHALL 将指标数据存储在组件状态中

#### Scenario: 指标数据展示

- **WHEN** 指标数据加载完成
- **THEN** 系统 SHALL 在工作流页面显示指标面板
- **AND** SHALL 按维度（身体姿态、上肢、下肢）分组展示指标
- **AND** 每个指标 SHALL 显示名称、数值、单位、可用性状态

#### Scenario: 指标数据加载失败

- **WHEN** 指标数据 API 调用失败
- **THEN** 系统 SHALL 显示友好的错误提示
- **AND** SHALL 提供手动重试按钮

### Requirement: 前端 SHALL 支持指标数据的持久化

系统 SHALL 支持将计算的指标数据持久化到后端，以便后续报告生成使用。

#### Scenario: 用户触发指标持久化

- **WHEN** 用户在指标面板点击"保存指标"按钮
- **THEN** 系统 SHALL 调用 `calculateMetrics` API 并设置 `persist=true`
- **AND** SHALL 显示保存成功提示

#### Scenario: 指标已持久化状态

- **WHEN** 指标数据已持久化
- **THEN** 系统 SHALL 在指标面板显示"已保存"状态
- **AND** SHALL 禁用"保存指标"按钮
