## ADDED Requirements

### Requirement: Mock model service accepts session analysis requests
Mock 阶段的模型服务 SHALL 接收业务后端发送的 session 级分析请求 schema。

#### Scenario: Backend sends session-level model request
- **WHEN** 业务后端向模型服务 `POST /api/v1/analyze` 发送包含 `task_id`、`session_id`、运动员信息、训练记录信息、`videos[]`、`callback_url` 和 `schema_version` 的请求
- **THEN** 模型服务 MUST 成功校验该请求，并不得要求旧单视频 `video_path`、`video_url` 和 `metadata` 顶层字段

#### Scenario: Request includes multiple videos
- **WHEN** 请求中的 `videos[]` 包含多个机位视频
- **THEN** 模型服务 MUST 保留或可读取每个视频的 `video_file_id`、`view_type`、`video_path`、`video_url`、`fps`、`resolution` 和 `sync_offset_ms`

### Requirement: Mock model service returns saveable swim result
Mock 阶段的模型服务 SHALL 返回业务后端可保存并可生成报告的稳定游泳分析结果。

#### Scenario: Mock inference completes
- **WHEN** 模型服务收到有效 session 级分析请求
- **THEN** 模型服务 MUST 返回 `status=completed`、`schema_version=swim-analysis.v1`、指标、诊断、阶段或关键点相关结构化字段

#### Scenario: Backend validates model response
- **WHEN** 业务后端使用 `ModelAnalysisResult` 校验模型服务响应
- **THEN** 响应 MUST 通过校验，并允许后端保存 `AnalysisResult`、更新任务为 `completed`、生成 session 报告

### Requirement: Mock provenance is explicit
模型服务 Mock 输出 SHALL 可被前端和报告识别为模拟分析结果。

#### Scenario: Mock result is transformed into report
- **WHEN** 后端基于 Mock 模型服务响应生成报告数据
- **THEN** 报告或结果来源 MUST 能标识为模型服务 Mock、模拟或非真实重模型推理
