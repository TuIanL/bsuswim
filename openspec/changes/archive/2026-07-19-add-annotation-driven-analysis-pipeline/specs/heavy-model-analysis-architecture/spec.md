# Capability: heavy-model-analysis-architecture

## MODIFIED Requirements

### Requirement: Analysis tasks support multiple pipeline types

AnalysisTask SHALL 不再只代表模型服务任务，执行器 SHALL 根据 pipeline_type 路由。

#### Scenario: Pipeline routing

- **WHEN** AnalysisTask 被创建
- **THEN** 系统 SHALL 持久化 pipeline_type 和 pipeline_version
- **AND** 执行器 SHALL 根据 pipeline_type 选择执行路径
- **AND** model_service pipeline 行为 SHALL 保持独立，不加载重模型

#### Scenario: Legacy model-service failure semantics remain isolated

- **WHEN** model_service pipeline 失败
- **THEN** 系统 SHALL 继续使用既有 `_set_task_state` 与 `_mark_failed` 行为
- **AND** 新增的结构化执行字段（execution_state / failed_stage / error_code）
      对于 model_service 任务 MAY 保持为空
- **AND** annotation_kinematics pipeline 的 checkpoint-aware 失败写入器
       MUST NOT 修改或重定义 `_mark_failed`
