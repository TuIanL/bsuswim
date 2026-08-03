## Context

导出链路（现状）：前端点击「导出 PDF」→ `POST /sessions/{id}/report/export/pdf` → 后端 `PdfExportService` 生成 2 分钟有效的 print token → Playwright 无头浏览器加载 `{pdf_render_base_url}/reports/{sessionId}/print?token=…` → SPA 路由渲染 `PrintReportView` → `fetch('/api/v1/internal/sessions/{id}/report/print-data?token=…')` 获取打印数据 → 资源就绪置 `window.__REPORT_PRINT_READY__` → `page.pdf()` 保存。

本地开发环境参数：前端 Vite dev server `127.0.0.1:5174`，后端 uvicorn `127.0.0.1:8001`（`start-web.command` 默认值），`pdf_render_base_url` 默认 `http://localhost:5174`。本地无 `.env` → `VITE_API_BASE_URL=''` → `demoMode=true`。

三个已知缺陷：
1. `vite.config.ts` 无 `/api` 代理，`PrintReportView` 相对路径 fetch 被 SPA fallback 成 index.html，print-data 永远拿不到（本地 demo 的直接原因）。
2. `/reports/:sessionId/print` 无 `meta.public`，非 demo 环境无登录态访问被守卫重定向 `/login`。
3. `playwright_renderer.py` 中 `wait_for_function` 失败被 `except: pass` 吞掉，无条件 `page.pdf()`，错误页面照样"导出成功"。

## Goals / Non-Goals

**Goals:**
- 本地 demo 模式（无 `VITE_API_BASE_URL`）下导出 PDF 能获取打印数据并渲染出五页报告。
- 非 demo 环境（`demoMode=false`）下 Playwright 无登录态访问 print 路由不被守卫拦截。
- 打印页渲染失败时导出必须明确失败（`pdf_status=export_failed` + 可读 `pdf_error`），绝不产出内容错误的"成功" PDF。
- 规范与实现对齐：修正 `pdf-export-service` 中 `Timeout fallback` 的错误语义，补充渲染校验与 demo 数据通道要求；`vue-auth-session-access` 补充 print 路由例外。

**Non-Goals:**
- 生产部署（nginx）的 `/api` 转发配置——属部署运维，本变更只保证 dev 代理与代码正确性。
- print token 存储机制改造（继续使用进程内存字典）。
- 五页报告布局、内容、AI 解读等报告本身的修改。
- 前端「下载 PDF」按钮、pdf_status 轮询等既有交互流程的改动。

## Decisions

### D1: Vite `/api` 开发代理打通 demo 数据通道

`vite.config.ts` 增加 `server.proxy`：`'/api' → http://127.0.0.1:8001`（与 `start-web.command` 的 `BACKEND_PORT` 默认值一致），target 允许通过 `VITE_DEV_PROXY_TARGET` 环境变量覆盖。

依据：`PrintReportView` 在 demo 模式（`apiBaseUrl=''`）下用相对路径 `fetch('/api/v1/...')`，代理后请求直达后端；部署环境 `VITE_API_BASE_URL` 非空时走绝对路径，行为不受影响。备选方案（打印页改用 axios client 携带 `baseURL`）被否：改动面更大、与 demo 数据层耦合更深。

### D2: print 路由标记公开，数据仍由 print token 保护

`router.ts` 中 `/reports/:sessionId/print` 增加 `meta: { public: true }`，守卫放行无登录态访问。

安全边界：路由放行 ≠ 数据开放——打印数据接口 `/api/v1/internal/sessions/{id}/report/print-data` 强制校验 URL 上的 print token（`purpose=pdf_export`、绑定 session/report_id、2 分钟有效、内存一次性）。无 token 或 token 无效时返回 401，`PrintReportView` 走既有 `fail()` 路径显示错误，`__REPORT_PRINT_ERROR__` 被设置。

### D3: Playwright 渲染结果校验，失败即中止

`backend/app/services/playwright_renderer.py` 改造 `render_pdf_from_url`：

1. `page.goto` 后校验 `page.url` 仍处于 print 路由（未被守卫重定向到 `/login` 等）——被重定向则抛错。
2. `wait_for_function("__REPORT_PRINT_READY__ === true")` 失败/超时 → 先读取 `window.__REPORT_PRINT_ERROR__`：存在则抛出对应 `code`/`message`，否则抛 `PRINT_READY_TIMEOUT`。
3. 全部通过后才调用 `page.pdf()`。

新增 `PdfRenderError(code, message)` 异常类（含 `PdfRenderTimeoutError` 语义），不再吞异常。`render_pdf_from_url` 抛出的异常向上传播至 `PdfExportService.export_report_pdf`，最终由路由层 `report_exports.py` 现有 `except Exception` 分支置 `pdf_status="export_failed"`、写入 `pdf_error`（该处理已存在，无需改路由）。

### D4: 规范语义修正

- `openspec/specs/pdf-export-service/spec.md`：
  - `Print readiness protocol` 的 `Timeout fallback` 场景改为：资源加载超过 30 秒时**必须**中止导出并标记失败，不得强制 ready 继续导出。
  - 新增需求「渲染结果校验」：ready 未置位、存在 `__REPORT_PRINT_ERROR__` 或被重定向时，系统 MUST 中止导出并将 `pdf_status` 置为 `export_failed`。
  - 新增需求「Demo 模式打印数据通道」：`VITE_API_BASE_URL` 未配置时，打印页 MUST 仍能获取 print-data 并成功生成报告 PDF。
- `openspec/specs/vue-auth-session-access/spec.md`：`Vue 路由权限` 增加 print 路由例外场景——访问 `/reports/:sessionId/print` 且 URL 携带有效 print token 时，系统 MUST 放行，不要求登录态。

### D5: 测试策略

- 后端 `backend/tests/test_pdf_export.py`：新增用例——mock `render_pdf_from_url` 抛 `PdfRenderError`，断言导出接口返回 500（`detail.code=pdf_export_failed`）、数据库 `pdf_status=export_failed`、`pdf_error` 非空；mock 重定向场景断言同样失败路径。
- 前端新增路由级测试（真实 `router` + pinia，关闭 demo）：未登录访问 `/reports/1/print` 放行渲染；未登录访问 `/reports/1` 仍重定向 `/login`；demo 模式访问 print 路由放行。

## Risks / Trade-offs

- **public 路由暴露面**：任何持有打印 URL 的人可在 token 有效期内（2 分钟）访问打印页。与既有 print token 设计一致（短期、绑定、一次性），可接受；无 token 时数据接口 401，页面仅显示错误。
- **`/api` 代理仅限 dev**：生产部署若 nginx 未配置 `/api` 转发，导出同样失败——这是部署配置问题而非代码缺陷，需在实施说明中提示。
- **代理 target 默认值**：硬编码 `127.0.0.1:8001`，与 `start-web.command` 默认一致；提供 `VITE_DEV_PROXY_TARGET` 覆盖，避免端口漂移。
- **超时时序**：前端 `PrintReadyRegistry` 超时（30s）置 `__REPORT_PRINT_ERROR__`，Playwright wait 超时（35s）读取该标志后中止，时序一致；Playwright 先行超时则抛 `PRINT_READY_TIMEOUT`，两者都导向 `export_failed`。
- **spec 语义变更**：推翻原 `Timeout fallback`"强制 ready 继续导出"的要求，属于行为修正；如文档（`docs/ai-report-interpretation-operations.md` 等）存在相悖描述，实施时顺带核对修正。
