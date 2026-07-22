## ADDED Requirements

### Requirement: 前端 SHALL 展示运动学诊断发现

系统 SHALL 在前端展示从后端生成的运动学诊断发现和建议，帮助教练理解分析结果。

#### Scenario: 分析完成后自动获取诊断发现

- **WHEN** 指标数据计算完成
- **AND** 存在对应的 `annotation_metric_id`
- **THEN** 系统 SHALL 自动调用 `generateReviewFindings` API 生成诊断发现
- **AND** SHALL 轮询 `getReviewFindings` API 直到生成完成

#### Scenario: 诊断发现展示

- **WHEN** 诊断发现数据加载完成
- **THEN** 系统 SHALL 在工作流页面显示诊断面板
- **AND** SHALL 按严重程度分组展示发现（警告、建议、信息）
- **AND** 每个发现 SHALL 显示标题、描述、相关指标、改进建议

#### Scenario: 诊断发现生成中状态

- **WHEN** 诊断发现正在生成中
- **THEN** 系统 SHALL 显示加载状态
- **AND** SHALL 显示正在分析的指标类型

#### Scenario: 诊断发现生成失败

- **WHEN** 诊断发现生成失败
- **THEN** 系统 SHALL 显示错误信息
- **AND** SHALL 提供重新生成按钮

### Requirement: 前端 SHALL 支持诊断发现的规则集选择

系统 SHALL 支持用户选择不同的诊断规则集，以获取不同维度的诊断建议。

#### Scenario: 用户选择规则集

- **WHEN** 用户在诊断面板选择规则集下拉框
- **AND** 选择新的规则集（如 `side_2d_kinematics_v1`）
- **THEN** 系统 SHALL 重新调用 `generateReviewFindings` API 并传入新的规则集
- **AND** SHALL 更新诊断发现展示
