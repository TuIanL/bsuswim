## ADDED Requirements

### Requirement: Backend-generated report data
互动报告 SHALL 使用后端基于模型分析结果生成的报告数据。

#### Scenario: User opens report for completed backend job
- **WHEN** 用户打开真实已完成任务的报告页
- **THEN** 报告页 MUST 从后端报告 API 加载训练摘要、关键指标、技术诊断、证据片段、图表数据和训练建议

#### Scenario: Report data is not ready
- **WHEN** 分析任务尚未完成或报告数据尚未生成
- **THEN** 报告页 MUST 显示处理中或不可用状态，并提供返回任务详情的操作

### Requirement: Report provenance clarity
报告 SHALL 区分真实模型输出、后端计算结果和 demo 数据。

#### Scenario: Real report is shown
- **WHEN** 报告模块展示真实模型服务输出或后端派生指标
- **THEN** 系统 MUST 标记数据来源、分析任务 ID 和报告生成时间

#### Scenario: Demo report is shown
- **WHEN** 系统使用 demo 数据展示报告
- **THEN** 报告 MUST 明确标记为 demo 或模拟内容，不得暗示来自真实 YOLO 类模型分析

### Requirement: PDF export remains future capability
报告 SHALL 以 HTML 页面作为第一版交付形态，并为 PDF 导出保留后期扩展边界。

#### Scenario: User views first-version report
- **WHEN** 用户打开第一版真实分析报告
- **THEN** 系统 MUST 展示完整 HTML 报告内容，包括图表、诊断和建议

#### Scenario: User expects PDF export before implementation
- **WHEN** PDF 导出尚未实现
- **THEN** 系统 MUST 不提供可点击的 PDF 导出操作，或将其明确标记为暂不可用
