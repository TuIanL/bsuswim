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

#### Scenario: Demo report is shown
- **WHEN** 系统使用 demo 数据展示报告
- **THEN** 报告 MUST 明确标记为 demo 或模拟内容，不得暗示来自真实 YOLO 类模型分析

### Requirement: PDF export remains future capability

报告 SHALL 支持将 HTML 报告内容导出为 PDF，由后端通过 Playwright 渲染前端 print route 生成，并提供下载入口。

#### Scenario: User exports report to PDF
- **WHEN** 用户点击"导出 PDF"按钮且报告 `report_data` 已就绪
- **THEN** 系统 MUST 调用 `POST /api/sessions/{session_id}/report/export/pdf`，返回可下载的 PDF URL

#### Scenario: User downloads exported PDF
- **WHEN** 用户点击"下载 PDF"按钮
- **THEN** 系统 MUST 通过 `GET /api/sessions/{session_id}/report/pdf` 返回 PDF 文件

#### Scenario: PDF export status is tracked
- **WHEN** PDF 正在导出或已导出/失败
- **THEN** 系统 MUST 通过 `GET /api/sessions/{session_id}/report/export/pdf/status` 返回当前状态、时间戳和错误信息

#### Scenario: Report uses frontend print route
- **WHEN** 后端 Playwright 需要渲染报告
- **THEN** 系统 MUST 使用前端专用 `/reports/{sessionId}/print` 路由，而非后端 Jinja2 模板

### Requirement: Report print route

系统 SHALL 提供前端专用 print route，复用现有 section-based 报告渲染组件。

#### Scenario: Print page uses existing renderer
- **WHEN** 用户或 Playwright 访问 `/reports/{sessionId}/print`
- **THEN** 系统 MUST 使用同一套 `ReportSectionRenderer` / `ModuleSection` / `ReportRadarChart` 组件渲染
- **THEN** 页面 MUST 应用打印专用 CSS（A4 横版尺寸、隐藏交互元素）

#### Scenario: Print route signals readiness
- **WHEN** print route 加载完毕且所有资源（图片、图表、字体）就绪
- **THEN** 页面 MUST 设置 `window.__REPORT_PRINT_READY__ = true`

### Requirement: Session report retrieval
报告 SHALL 支持按训练记录读取后端生成的报告数据。

#### Scenario: Frontend requests report by session
- **WHEN** 前端请求 `GET /api/v1/reports/{session_id}`
- **THEN** 系统 MUST 返回该训练记录对应的报告数据，或在报告不存在时返回稳定不可用状态

#### Scenario: Report generation is requested
- **WHEN** 前端请求 `POST /api/v1/reports/generate` 并提交已完成分析的 `session_id`
- **THEN** 系统 MUST 基于该训练记录的分析结果生成或刷新报告数据

### Requirement: Vue report navigation uses session identity
真实后端模式下，Vue 报告页 SHALL 使用训练记录 ID 读取报告数据，并从完成任务上下文中获得该训练记录 ID。

#### Scenario: User opens report from completed workspace
- **WHEN** 用户从已完成真实任务的工作台点击查看报告
- **THEN** 前端 MUST 导航到该任务所属 `session_id` 对应的报告页，并请求 `GET /api/v1/reports/{session_id}`

#### Scenario: User opens report from task management
- **WHEN** 用户在任务管理中打开已完成训练记录的报告
- **THEN** 前端 MUST 使用训练记录 ID 读取报告，而不是把 `task_id` 当作报告 ID

### Requirement: Report readiness handling
Vue 报告页 SHALL 对真实后端报告未生成或不可用状态提供稳定反馈。

#### Scenario: Report does not exist yet
- **WHEN** 前端请求 `GET /api/v1/reports/{session_id}` 且后端返回报告尚未生成
- **THEN** 报告页 MUST 显示报告未就绪状态，并提供返回任务管理或刷新报告的操作

#### Scenario: Report can be generated on demand
- **WHEN** 训练记录已有已完成分析结果但报告不存在
- **THEN** 前端 MAY 调用 `POST /api/v1/reports/generate` 并提交 `session_id`，成功后展示生成的报告数据

### Requirement: Report keeps provenance for mocked model output
报告 SHALL 在模型服务仍为 Mock 时清晰标识数据来源。

#### Scenario: Mock model report is shown
- **WHEN** 报告数据来源于 session 级 Mock 模型服务或后端派生 Mock 结果
- **THEN** 报告页 MUST 展示来源、训练记录 ID、分析任务 ID 和生成时间，并不得暗示结果来自真实重模型推理

### Requirement: Frontend renders swim-report.v1 sections

前端报告页 SHALL 支持渲染后端 swim-report.v1 产出的 `sections` 数组，并在缺少 `section.type` 字段时通过 section key 映射进行渲染。

#### Scenario: Sections array is rendered in order
- **WHEN** `report_data.sections` 包含多个 section 对象
- **THEN** 前端 MUST 按数组顺序渲染每个 section，每个 section 使用其对应的 renderer 组件

#### Scenario: Unknown section key does not break page
- **WHEN** section 包含不在渲染映射表中的 key
- **THEN** 前端 MUST 使用 GenericSection 渲染，不引发页面崩溃或白屏

