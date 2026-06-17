## ADDED Requirements

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
