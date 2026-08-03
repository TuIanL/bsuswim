## 1. 前端：打通 demo 模式打印数据通道

- [x] 1.1 在 `frontend-vue/vite.config.ts` 增加 `server.proxy`：`'/api'` 代理到 `http://127.0.0.1:8001`，target 允许通过 `VITE_DEV_PROXY_TARGET` 环境变量覆盖（与 `start-web.command` 的 `BACKEND_PORT` 默认值一致）
- [x] 1.2 验证 demo 模式（无 `.env`）下打印页 `fetch('/api/v1/internal/.../print-data')` 能通过代理到达后端并返回数据（本地手动验证或补代理配置断言）——已启动 dev server 实测：`/api` 请求返回后端 404 语义（非 SPA fallback 的 index.html），代理生效

## 2. 前端：print 路由公开访问

- [x] 2.1 在 `frontend-vue/src/router.ts` 为 `/reports/:sessionId/print` 添加 `meta: { public: true }`，使全局守卫放行无登录态访问（数据仍由 URL print token 鉴权）

## 3. 后端：Playwright 渲染结果校验

- [x] 3.1 在 `backend/app/services/playwright_renderer.py` 新增 `PdfRenderError(code, message)` 异常类（`PdfRenderTimeoutError` 改为继承它）
- [x] 3.2 `page.goto` 完成后校验 `page.url` 仍处于 print 路由（未被守卫重定向到 `/login` 等）；被重定向则抛 `PdfRenderError('PRINT_ROUTE_REDIRECTED')`
- [x] 3.3 `wait_for_function("__REPORT_PRINT_READY__ === true")` 失败/超时不再 `except: pass`：先读取 `window.__REPORT_PRINT_ERROR__`，存在则抛对应 code/message，否则抛 `PRINT_READY_TIMEOUT`
- [x] 3.4 仅当就绪校验全部通过后才调用 `page.pdf()`，移除无条件导出路径

## 4. 后端：导出失败状态落地

- [x] 4.1 `report_exports.py` 的 `except Exception` 分支透传 `PdfRenderError`：`pdf_error` 格式化为 `[code] message`，其余异常保持 `str(exc)`
- [x] 4.2 确认渲染失败不残留 `exporting` 状态（失败置 `export_failed`）、print token 2 分钟自动过期无泄漏

## 5. 后端测试

- [x] 5.1 `backend/tests/test_pdf_export.py` 新增 `test_export_render_error_marks_failed`：mock `PdfExportService` 抛 `PdfRenderError('PRINT_READY_TIMEOUT')`，断言 500 / `pdf_export_failed` / DB `export_failed` / `pdf_error` 含 `[PRINT_READY_TIMEOUT]`
- [x] 5.2 新增 `test_export_redirected_route_aborts_without_pdf`：mock `render_pdf_from_url` 抛 `PRINT_ROUTE_REDIRECTED`，断言异常向上传播、`save_bytes` 未调用、未置 exported（无假成功）

## 6. 前端测试

- [x] 6.1 新增 `src/router.guard.spec.ts`（`vi.doMock` 控制 demoMode + 动态 import router + 全部 view stub）：非 demo 未登录访问 `/reports/1/print` 放行且 `meta.public=true`；访问 `/reports/1` 重定向 `/login` 且带 `redirect` query
- [x] 6.2 同文件 demo 模式用例：访问 `/reports/1/print` 放行

## 7. 规范与文档同步

- [x] 7.1 检查 `docs/`：无与 PDF 超时/导出失败行为相悖的描述（相关超时均属 AI 解读模块），无需修改
- [x] 7.2 `openspec validate --changes fix-pdf-export-print-pipeline` 通过；任务全部勾选
