## ADDED Requirements

### Requirement: Analysis task detail API for frontend integration
业务后端 SHALL 提供前端连调所需的分析任务读取能力，使 Vue 前端能从 `task_id` 获得任务所属训练记录和可用操作。

#### Scenario: Frontend reads analysis task detail
- **WHEN** 已登录调用方请求真实分析任务详情或正式 analysis workspace 聚合 API
- **THEN** 系统 MUST 返回任务 ID、训练记录 ID、状态、阶段、进度、错误信息、时间戳和可用操作

#### Scenario: Unauthorized task is requested
- **WHEN** 调用方请求不属于当前用户可访问训练记录的分析任务
- **THEN** 系统 MUST 返回稳定的未找到或未授权错误，不得泄露其他用户任务数据

### Requirement: Analysis workspace data contract
业务后端 SHALL 支持前端加载真实工作台所需的数据组合。

#### Scenario: Workspace data is requested for completed task
- **WHEN** 已登录调用方请求已完成任务的工作台数据
- **THEN** 系统 MUST 返回任务状态、分析结果、训练记录 ID 和该训练记录已绑定视频的文件摘要与播放 URL

#### Scenario: Workspace data is requested before result exists
- **WHEN** 已登录调用方请求尚未完成或没有结果的任务工作台数据
- **THEN** 系统 MUST 返回任务状态和训练记录上下文，并以空结果或稳定错误表达结果尚不可用

### Requirement: Completed analysis exposes session report path
业务后端 SHALL 保证完成的分析任务可以关联到 session 级报告读取。

#### Scenario: Model result is saved for a task
- **WHEN** 后端保存模型服务返回的有效分析结果并将任务更新为 `completed`
- **THEN** 系统 MUST 创建或刷新该任务所属训练记录的报告元数据，使 `GET /api/v1/reports/{session_id}` 可读取报告

#### Scenario: Report generation fails after result save
- **WHEN** 分析结果已保存但报告生成失败
- **THEN** 系统 MUST 保留任务完成或失败状态的一致性，并返回可读错误用于前端展示或重试生成报告
