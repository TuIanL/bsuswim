# vue-auth-session-access (delta)

## MODIFIED Requirements

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

#### Scenario: Print route bypasses login

- **WHEN** 未登录用户（非 demo 模式）访问 `/reports/:sessionId/print` 且 URL 携带 print token
- **THEN** 系统 MUST 放行打印路由渲染，不跳转 `/login`（打印页数据仍由 print token 鉴权）

#### Scenario: Report route still requires login

- **WHEN** 未登录用户（非 demo 模式）访问 `/reports/:sessionId`（报告主路由，无 print token）
- **THEN** 系统 MUST 仍拦截访问并跳转到 `/login`
