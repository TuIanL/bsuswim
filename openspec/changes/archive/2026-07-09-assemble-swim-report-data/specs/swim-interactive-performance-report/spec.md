## MODIFIED Requirements

### Requirement: Backend-generated report data

互动报告 SHALL 使用后端基于模型分析结果或 `annotation_metrics + diagnostics` 生成的报告数据。

#### Scenario: User opens legacy report for completed backend job
- **WHEN** 用户打开已完成训练记录的报告页，且报告来源于模型服务输出
- **THEN** 报告页 MUST 从后端 session 报告 API 加载运动员信息、训练记录摘要、关键指标、技术诊断、证据片段、图表数据和训练建议

#### Scenario: User opens swim-report.v1 for completed pipeline
- **WHEN** 用户打开已完成 `annotation_metrics + diagnostics` 计算的训练记录报告页
- **THEN** 报告页 MUST 从后端 session 报告 API 加载 swim-report.v1 结构化数据，包含模块化 sections、canonical metrics、diagnostic 分组的 findings 和 recommendations

#### Scenario: Report data is not ready
- **WHEN** 训练记录分析任务尚未完成或报告数据尚未生成
- **THEN** 报告页 MUST 显示处理中或不可用状态，并提供返回训练记录或任务详情的操作

### Requirement: Report generation timing is decoupled from analysis save

报告生成 MUST 不再绑定在 `save_analysis_result()` 内同步完成唯一的完整报告。legacy 报告仍随 save_analysis_result 生成，swim-report.v1 报告需在 `annotation_metrics + diagnostics` 就绪后显式触发。

#### Scenario: Swim report generation requires ready inputs
- **WHEN** 系统收到 swim-report.v1 生成请求但 `annotation_metrics` 或 `diagnostics` 未就绪
- **THEN** 系统 MUST 返回 409/422 提示先完成指标计算或规则诊断

#### Scenario: Swim report is generated on demand
- **WHEN** 前端或服务显式请求 `POST /api/v1/analysis-results/{id}/build-swim-report`
- **THEN** 系统 MUST 检查 `annotation_metrics` 和 `diagnostics` 完备性，就绪后生成 swim-report.v1 并更新 `ReportMetadata.report_data`

### Requirement: Report provenance clarity

报告 SHALL 区分真实模型输出、后端计算结果和 demo 数据。

#### Scenario: Real report is shown
- **WHEN** 报告模块展示真实模型服务输出或后端派生指标
- **THEN** 系统 MUST 标记数据来源、训练记录 ID、分析任务 ID 和报告生成时间，swim-report.v1 额外标注 `source_trace.annotation_metric_id`
