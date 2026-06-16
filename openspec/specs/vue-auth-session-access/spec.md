# vue-auth-session-access Specification

## Purpose
定义 `frontend-vue` 的登录注册、会话恢复、角色感知导航和路由访问控制要求。

## Requirements
### Requirement: Vue 登录与注册页面
`frontend-vue` SHALL provide login and registration pages for coaches, athletes, and administrators.

#### Scenario: User opens login page
- **WHEN** 未登录用户打开 `/login`
- **THEN** 系统 MUST 展示用户名、密码、记住登录状态和登录动作，并提供进入注册页的入口

#### Scenario: User opens register page
- **WHEN** 未登录用户打开 `/register`
- **THEN** 系统 MUST 展示姓名、用户名、手机号、邮箱、密码和角色选择字段，角色选择至少包含教练、运动员和管理员

#### Scenario: User submits valid registration
- **WHEN** 用户提交有效注册信息
- **THEN** 系统 MUST 调用注册 API 创建用户，并在成功后引导用户登录或自动建立会话

### Requirement: Vue 会话保存与恢复
`frontend-vue` SHALL persist and restore authenticated user sessions across browser reloads.

#### Scenario: Login succeeds
- **WHEN** 用户使用正确账号密码登录成功
- **THEN** 系统 MUST 保存 `access_token`、用户资料和角色，并将后续 API 请求附带 `Authorization: Bearer <access_token>`

#### Scenario: User reloads browser
- **WHEN** 浏览器刷新且本地存在未清除的 `access_token`
- **THEN** 系统 MUST 尝试通过当前用户 API 恢复用户资料，并保持已登录状态

#### Scenario: Session is invalid
- **WHEN** 当前用户 API 返回未授权或 token 失效
- **THEN** 系统 MUST 清除本地会话并跳转到 `/login`

### Requirement: Vue 路由权限
`frontend-vue` SHALL enforce route access based on authentication state and user role.

#### Scenario: Anonymous user opens protected page
- **WHEN** 未登录用户在非 demo 模式下打开运动员、测试任务、上传、工作台或报告页面
- **THEN** 系统 MUST 阻止访问并跳转到 `/login`

#### Scenario: Authenticated user opens auth page
- **WHEN** 已登录用户打开 `/login` 或 `/register`
- **THEN** 系统 MUST 跳转到默认业务入口 `/athletes`

#### Scenario: Coach opens management pages
- **WHEN** 教练角色用户打开运动员管理、测试任务创建或多机位上传页面
- **THEN** 系统 MUST 允许访问并展示教练可用操作

#### Scenario: Athlete role opens management pages
- **WHEN** 运动员角色用户尝试打开教练管理页面
- **THEN** 系统 MUST 隐藏或禁用管理操作，并只保留其可查看的档案和报告入口

### Requirement: Demo authentication mode
`frontend-vue` SHALL allow the core workflow to be browsed without backend API configuration.

#### Scenario: API base URL is not configured
- **WHEN** `VITE_API_BASE_URL` 未配置
- **THEN** 系统 MUST 使用 demo 用户和 demo 数据，使用户可以进入核心业务页面而不需要真实登录

#### Scenario: Demo user logs out
- **WHEN** demo 模式用户触发登出
- **THEN** 系统 MUST 清除当前页面会话状态，并允许用户重新进入 demo 流程
