## Why

用户在本地开发环境点击「导出 PDF」后，得到的 PDF 内容是整个应用的首页/错误页，而不是报告的五页内容，且界面显示"导出成功"（pdf_status=exported）。

诊断出三个根因，共同导致打印页从未被正确渲染：

1. **本地 demo 模式打印数据通道断裂（本次用户现场的直接原因）**：本地未配置 `VITE_API_BASE_URL`（`demoMode=true`），打印页 `PrintReportView` 用相对路径 `fetch('/api/v1/internal/sessions/{id}/report/print-data')`，而 `vite.config.ts` 未配置 `/api` 开发代理——请求被 Vite SPA fallback 成 index.html，打印数据永远拿不到，打印页渲染失败。
2. **打印路由未标记公开**：`/reports/:sessionId/print` 没有 `meta: { public: true }`。非 demo 环境（部署/联调，`demoMode=false`）下，Playwright 无头浏览器（全新上下文、无登录态）访问打印路由会被全局路由守卫重定向到 `/login`，PDF 内容变成登录页。打印页本身通过 URL 上的短时 print token 鉴权，本就不应要求登录态。
3. **渲染结果无兜底校验（假成功放大器）**：`playwright_renderer.py` 中 `wait_for_function("__REPORT_PRINT_READY__ === true")` 失败/超时被 `except: pass` 吞掉，之后**无条件**执行 `page.pdf()`。打印页无论加载失败、被重定向还是仍在加载，都会产出一个"看似成功"的 PDF，且后端把 `pdf_status` 置为 `exported`——用户拿到的是内容错误的 PDF 却没有任何报错信号。

此外，现有 spec `pdf-export-service` 的 `Timeout fallback` 场景要求"资源加载超过 30 秒时强制设置 ready 并继续导出"，与本次"失败必须可见"的目标相悖，属于 spec 与实现的双重错误，需一并修正。

## What Changes

**前端（frontend-vue）**
- `vite.config.ts` 增加 `/api` 开发代理（指向后端），打通本地 demo 模式打印页获取 print-data 的数据通道；`/api/v1/internal` 等路径全部走代理。
- `router.ts` 为 `/reports/:sessionId/print` 添加 `meta: { public: true }`，使无登录态访问放行（打印页自行通过 URL print token 鉴权）。

**后端（backend）**
- `playwright_renderer.py`：渲染结果校验——`wait_for_function` 失败或超时、页面出现 `window.__REPORT_PRINT_ERROR__`、最终 URL 已离开 print 路由（被重定向）时，抛 `PdfRenderError` 中止，不再无条件 `page.pdf()`。
- `pdf_export_service.py`：捕获渲染错误，将报告 `pdf_status` 置为 `export_failed` 并写入可读 `pdf_error`，前端按既有 `pdf_export_failed` 流程提示用户。

**规范（openspec/specs）**
- 修改 `pdf-export-service`：
  - 修正 `Print readiness protocol` 的 `Timeout fallback` 场景——超时不得强制 ready 继续导出，必须失败并中止导出。
  - 新增"渲染结果校验"需求：Playwright 必须确认 ready 标志且无错误标志后才生成 PDF，失败时导出必须标记为失败。
  - 新增 demo 模式打印数据通道需求：`VITE_API_BASE_URL` 未配置（demo 模式）下，打印页仍须能获取 print-data 并生成报告 PDF。
- 修改 `vue-auth-session-access`：`Vue 路由权限` 增加 print 路由例外场景——携带有效 print token 的 `/reports/:sessionId/print` 访问不要求登录态。

**测试**
- 前端：路由级测试验证未登录（demo 关闭）时 print 路由放行、其他受保护路由仍拦截。
- 后端：测试渲染失败（ready 未置位/页面报错）时导出中止并置 `export_failed`，且不产出 PDF 文件。

## Capabilities

### New Capabilities

（无）

### Modified Capabilities
- `pdf-export-service`: 修正 Timeout fallback 语义（超时必须失败而非强制 ready）；新增渲染结果校验要求（未就绪/页面报错不得产出 PDF，失败置 export_failed）；新增 demo 模式打印数据通道要求（无 VITE_API_BASE_URL 时打印页仍可获取数据）。
- `vue-auth-session-access`: `Vue 路由权限` 新增 print 路由例外场景（带 print token 的打印路由不要求登录态）。

## Impact

- `backend/app/services/playwright_renderer.py`：新增渲染结果校验与错误类型。
- `backend/app/services/pdf_export_service.py`：渲染失败时的状态处理。
- `backend/tests/test_pdf_export.py`：新增渲染失败用例（现有 mock 需要扩展）。
- `frontend-vue/src/router.ts`：print 路由 meta 标记。
- `frontend-vue/vite.config.ts`：`/api` 开发代理。
- `frontend-vue/src/views/PrintReportView.spec.ts` 或新增路由测试：print 路由访问控制用例。
- `openspec/specs/pdf-export-service/spec.md`、`openspec/specs/vue-auth-session-access/spec.md`：需求与场景更新。
- 无 API 契约变更、无数据库迁移、无新增依赖。
