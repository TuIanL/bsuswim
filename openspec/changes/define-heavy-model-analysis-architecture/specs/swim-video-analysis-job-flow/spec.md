## ADDED Requirements

### Requirement: Backend analysis job creation
系统 SHALL 通过业务后端创建真实游泳视频分析任务。

#### Scenario: User submits real video analysis
- **WHEN** 用户选择有效视频文件并填写必需的训练元数据后提交分析
- **THEN** 前端 MUST 通过 API 上传视频并创建后端分析任务，而不是只创建本地 demo job

#### Scenario: Backend returns created job
- **WHEN** 后端成功创建分析任务
- **THEN** 系统 MUST 返回任务 ID、初始状态、视频元数据、训练元数据和后续状态查询入口

### Requirement: Backend task polling
系统 SHALL 支持前端查询真实分析任务状态。

#### Scenario: User opens task management with backend enabled
- **WHEN** 前端配置了业务后端 API
- **THEN** 任务管理视图 MUST 从后端加载任务列表，并展示数据库中的状态、进度、更新时间和可用操作

#### Scenario: User opens processing task
- **WHEN** 用户打开正在处理的任务
- **THEN** 前端 MUST 轮询或刷新任务详情 API，并展示后端返回的当前阶段和进度

### Requirement: Model-service-backed terminal states
系统 SHALL 根据模型服务和结果保存过程更新任务终态。

#### Scenario: Model result is saved
- **WHEN** 模型服务返回有效分析结果且业务后端保存成功
- **THEN** 任务状态 MUST 更新为 `completed`，并暴露可进入可视化工作台和报告页的操作

#### Scenario: Model service fails
- **WHEN** 模型服务返回错误、超时或输出无法验证
- **THEN** 任务状态 MUST 更新为 `failed`，并展示后端保存的错误原因
