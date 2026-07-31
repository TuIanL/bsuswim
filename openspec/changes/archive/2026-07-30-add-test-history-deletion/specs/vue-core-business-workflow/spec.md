## MODIFIED Requirements

### Requirement: Vue 运动员档案
`frontend-vue` SHALL provide an athlete profile page that supports later long-term tracking and deletion of owned historical tests.

#### Scenario: User opens athlete profile
- **WHEN** 用户打开 `/athletes/:athleteId`
- **THEN** 系统 MUST 展示基础信息卡片、最近一次技术评分、历史测试记录表、核心指标趋势预览和创建新测试按钮

#### Scenario: Athlete has session history
- **WHEN** 运动员存在历史测试记录
- **THEN** 系统 MUST 展示测试日期、泳姿、距离、评分、状态和可用操作

#### Scenario: Athlete has no session history
- **WHEN** 运动员没有历史测试记录
- **THEN** 系统 MUST 展示稳定空状态，并提供创建新测试入口

#### Scenario: Coach deletes a history row
- **WHEN** 当前教练在运动员档案的历史记录中确认删除一条测试
- **THEN** 系统 MUST 调用训练记录删除 API
- **AND** 成功后 MUST 从历史记录和趋势数据中移除该测试

## ADDED Requirements

### Requirement: Vue 测试任务删除
`frontend-vue` SHALL 在测试任务列表为当前教练提供不可恢复的单条测试删除操作。

#### Scenario: Coach confirms task deletion
- **WHEN** 教练点击测试任务行的删除操作并在确认框中确认
- **THEN** 确认框 MUST 明确说明视频、报告和分析数据将被永久删除
- **AND** 系统 MUST 调用 `DELETE /api/v1/sessions/{sessionId}`

#### Scenario: Deletion succeeds
- **WHEN** 删除 API 返回成功
- **THEN** 系统 MUST 刷新测试任务和历史记录数据
- **AND** 被删除行 MUST 不再显示

#### Scenario: Deletion is rejected or fails
- **WHEN** 删除 API 返回冲突或错误
- **THEN** 系统 MUST 保留原任务行
- **AND** 系统 MUST 显示后端返回的可理解错误信息

#### Scenario: Demo mode deletes a demo test
- **WHEN** 系统处于 demo 模式且用户确认删除一条示例测试
- **THEN** 系统 MUST 从内存中的示例会话、任务和会话视频集合移除该测试关联数据
