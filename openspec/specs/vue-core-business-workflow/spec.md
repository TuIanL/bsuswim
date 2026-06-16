# vue-core-business-workflow Specification

## Purpose
定义 `frontend-vue` 第一批核心业务闭环页面：运动员管理、运动员档案、测试任务创建、多机位上传和 demo 业务数据。

## Requirements
### Requirement: Vue 运动员列表
`frontend-vue` SHALL provide an athlete list page as the coach's primary business entry.

#### Scenario: Coach opens athlete list
- **WHEN** 教练打开 `/athletes`
- **THEN** 系统 MUST 展示运动员表格，包含姓名、性别、年龄、主项、所属队伍、最近测试时间、当前技术评分和操作入口

#### Scenario: Coach filters athletes
- **WHEN** 教练输入姓名、选择泳姿、选择队伍或设置技术评分区间
- **THEN** 系统 MUST 根据筛选条件更新运动员列表，后端暂不支持的条件可以在前端本地筛选或显示为预留筛选项

#### Scenario: Coach creates athlete
- **WHEN** 教练点击新建运动员并提交有效运动员信息
- **THEN** 系统 MUST 创建运动员并刷新列表

#### Scenario: Coach chooses athlete action
- **WHEN** 教练在运动员行点击查看档案或创建测试
- **THEN** 系统 MUST 分别跳转到运动员档案页或带有运动员上下文的测试任务创建页

### Requirement: Vue 运动员档案
`frontend-vue` SHALL provide an athlete profile page that supports later long-term tracking.

#### Scenario: User opens athlete profile
- **WHEN** 用户打开 `/athletes/:athleteId`
- **THEN** 系统 MUST 展示基础信息卡片、最近一次技术评分、历史测试记录表、核心指标趋势预览和创建新测试按钮

#### Scenario: Athlete has session history
- **WHEN** 运动员存在历史测试记录
- **THEN** 系统 MUST 展示测试日期、泳姿、距离、评分、状态和可用操作

#### Scenario: Athlete has no session history
- **WHEN** 运动员没有历史测试记录
- **THEN** 系统 MUST 展示稳定空状态，并提供创建新测试入口

### Requirement: Vue 测试任务创建
`frontend-vue` SHALL provide a training session creation page that connects athletes to video upload.

#### Scenario: Coach opens create session page
- **WHEN** 教练打开 `/sessions/new`，且已选择或传入运动员
- **THEN** 系统 MUST 展示运动员选择、测试日期、泳姿、距离、泳池长度、场景和备注字段

#### Scenario: Coach submits valid session
- **WHEN** 教练提交有效测试任务信息
- **THEN** 系统 MUST 调用后端创建 `TrainingSession`，并跳转到 `/sessions/:sessionId/upload`

#### Scenario: Create session is missing athlete
- **WHEN** 用户未选择运动员就提交测试任务
- **THEN** 系统 MUST 阻止提交并提示选择运动员

### Requirement: Vue 多机位视频上传
`frontend-vue` SHALL provide a multi-camera upload page for a specific training session.

#### Scenario: User opens session upload page
- **WHEN** 用户打开 `/sessions/:sessionId/upload`
- **THEN** 系统 MUST 展示当前测试任务信息，以及侧面、正面、俯视、水下、半水下机位上传卡片

#### Scenario: User uploads camera video
- **WHEN** 用户在任一机位卡片选择有效视频文件
- **THEN** 系统 MUST 上传视频文件，绑定到当前 `TrainingSession`，记录机位类型、文件名、文件大小、上传状态和 `sync_offset_ms`

#### Scenario: User edits sync offset
- **WHEN** 用户为已上传或待上传机位填写同步偏移
- **THEN** 系统 MUST 将偏移值按毫秒保存到该机位视频对象中

#### Scenario: User saves draft
- **WHEN** 用户点击保存草稿
- **THEN** 系统 MUST 保留当前已上传机位和同步偏移状态，并停留在上传页

#### Scenario: User submits analysis
- **WHEN** 用户点击提交分析
- **THEN** 系统 MUST 检查至少存在一个成功绑定的视频，并进入后续分析状态或显示后端暂未接入的明确提示

### Requirement: Vue 业务 demo 数据
`frontend-vue` SHALL provide realistic demo data for the first-batch business workflow when backend API is unavailable.

#### Scenario: Demo mode athlete workflow
- **WHEN** 系统处于 demo 模式且用户打开运动员列表或档案
- **THEN** 系统 MUST 展示可操作的示例运动员、示例历史测试和示例指标趋势

#### Scenario: Demo mode session workflow
- **WHEN** 系统处于 demo 模式且用户创建测试任务或上传多机位视频
- **THEN** 系统 MUST 返回稳定的示例会话和上传状态，使页面流程可以完整演示
