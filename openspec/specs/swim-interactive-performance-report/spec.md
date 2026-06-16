# swim-interactive-performance-report Specification

## Purpose
TBD - created by archiving change port-pickleball-platform-to-swim-analysis. Update Purpose after archive.
## Requirements
### Requirement: Swim performance report
The system SHALL provide interactive swim analysis reports based on demo or job-specific report data.

#### Scenario: User opens a swim report
- **WHEN** the user opens a report view
- **THEN** the system displays session context, summary metrics, key findings, and report-source clarity for the selected swim analysis job or demo dataset

#### Scenario: Report data is limited
- **WHEN** a report module lacks algorithm-derived data
- **THEN** the system labels the module as demo, unavailable, or limited rather than presenting unsupported metrics as real analysis

### Requirement: Swim posture diagnostics
The report SHALL surface coach-readable posture and technique diagnostics.

#### Scenario: User reviews diagnostic findings
- **WHEN** diagnostic findings are available
- **THEN** the system displays issue title, severity, evidence, coach suggestion, expected improvement, and priority for swim-specific topics such as body line, breathing timing, hand entry, catch, kick rhythm, or hip rotation

### Requirement: Stroke rhythm and symmetry metrics
The report SHALL include swim-specific metrics that can support training comparison.

#### Scenario: User reviews metric cards
- **WHEN** report metrics are visible
- **THEN** the system shows metrics such as stroke rhythm, body angle stability, left-right symmetry, kick consistency, breathing timing, and overall technique score

#### Scenario: User reviews trend or progress information
- **WHEN** trend data is available
- **THEN** the system presents the change in readable units and does not imply precision beyond the available demo or algorithm source

### Requirement: Training feedback loop
The system SHALL translate swim analysis findings into training recommendations.

#### Scenario: User opens training feedback
- **WHEN** the user opens the training view
- **THEN** the system displays recommended drills, linked technique issues, practice tasks, target outcomes, and progress toward the next training goal

#### Scenario: User follows a recommendation from a report
- **WHEN** the user selects a training recommendation from a report or workspace
- **THEN** the system opens the training feedback context associated with that analysis or demo recommendation

### Requirement: Report visual consistency
Report and training views SHALL retain the dark 智泳云枢 platform design language.

#### Scenario: User compares report views with homepage
- **WHEN** the user moves from the homepage into reports or training feedback
- **THEN** typography, color, panel treatment, icon usage, spacing, and interaction states feel like one product rather than an imported bright dashboard

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

### Requirement: PDF export remains future capability
报告 SHALL 以 HTML 页面作为第一版交付形态，并为 PDF 导出保留后期扩展边界。

#### Scenario: User views first-version report
- **WHEN** 用户打开第一版真实分析报告
- **THEN** 系统 MUST 展示完整 HTML 报告内容，包括图表、诊断和建议

#### Scenario: User expects PDF export before implementation
- **WHEN** PDF 导出尚未实现
- **THEN** 系统 MUST 不提供可点击的 PDF 导出操作，或将其明确标记为暂不可用

### Requirement: Session report retrieval
报告 SHALL 支持按训练记录读取后端生成的报告数据。

#### Scenario: Frontend requests report by session
- **WHEN** 前端请求 `GET /api/v1/reports/{session_id}`
- **THEN** 系统 MUST 返回该训练记录对应的报告数据，或在报告不存在时返回稳定不可用状态

#### Scenario: Report generation is requested
- **WHEN** 前端请求 `POST /api/v1/reports/generate` 并提交已完成分析的 `session_id`
- **THEN** 系统 MUST 基于该训练记录的分析结果生成或刷新报告数据

