## MODIFIED Requirements

### Requirement: Backend-generated report data
互动报告 SHALL 使用后端基于模型分析结果生成的报告数据。

#### Scenario: User opens report for completed backend job
- **WHEN** 用户打开真实已完成训练记录的报告页
- **THEN** 报告页 MUST 从后端 session 报告 API 加载运动员信息、训练记录摘要、关键指标、技术诊断、证据片段、图表数据和训练建议

#### Scenario: Report data is not ready
- **WHEN** 训练记录分析任务尚未完成或报告数据尚未生成
- **THEN** 报告页 MUST 显示处理中或不可用状态，并提供返回训练记录或任务详情的操作

### Requirement: Report provenance clarity
报告 SHALL 区分真实模型输出、后端计算结果和 demo 数据。

#### Scenario: Real report is shown
- **WHEN** 报告模块展示真实模型服务输出或后端派生指标
- **THEN** 系统 MUST 标记数据来源、训练记录 ID、分析任务 ID 和报告生成时间

#### Scenario: Demo report is shown
- **WHEN** 系统使用 demo 数据展示报告
- **THEN** 报告 MUST 明确标记为 demo 或模拟内容，不得暗示来自真实 YOLO 类模型分析

## ADDED Requirements

### Requirement: Session report retrieval
报告 SHALL 支持按训练记录读取后端生成的报告数据。

#### Scenario: Frontend requests report by session
- **WHEN** 前端请求 `GET /api/v1/reports/{session_id}`
- **THEN** 系统 MUST 返回该训练记录对应的报告数据，或在报告不存在时返回稳定不可用状态

#### Scenario: Report generation is requested
- **WHEN** 前端请求 `POST /api/v1/reports/generate` 并提交已完成分析的 `session_id`
- **THEN** 系统 MUST 基于该训练记录的分析结果生成或刷新报告数据
