## ADDED Requirements

### Requirement: PDF export uses frontend print route

系统 SHALL 使用 Playwright 打开前端专用 print route（非 Jinja2 后端模板）生成 PDF 报告。

#### Scenario: Export triggers frontend print
- **WHEN** 用户请求 PDF 导出
- **THEN** 系统 MUST 通过 Playwright 打开前端 `/reports/{sessionId}/print?token={token}` 路由进行渲染
- **THEN** 后端 MUST 不维护独立 Jinja2 报告模板

### Requirement: Export API uses session-level key

PDF 导出相关 API SHALL 使用 `session_id` 作为公开查找键，匹配现有前端 `/reports/:sessionId` 路由。公共 API 路径从 `/api/sessions/{session_id}/report/export/pdf` 模式正式定为 `/sessions/{session_id}/report/export/pdf`（无 `/reports` 前缀）。

#### Scenario: Export by session
- **WHEN** 前端持有 sessionId 请求 PDF 导出
- **THEN** 系统 MUST 接受 `POST /sessions/{session_id}/report/export/pdf`
- **THEN** 后端 MUST 从 session_id 内部解析到 ReportMetadata 记录
- **THEN** 路由 MUST NOT 包含 `/reports` 前缀

### Requirement: Print token guards the print route

系统 SHALL 使用短时 print token 鉴权 Playwright 对 print route 的访问，不得暴露无鉴权内部页面。

#### Scenario: Token is required
- **WHEN** Playwright 请求 print route
- **THEN** URL MUST 包含 `token` 参数
- **WHEN** token 无效、过期或 purpose 不匹配
- **THEN** 系统 MUST 返回 401/403

#### Scenario: Token expires quickly
- **WHEN** PDF 导出服务生成 print token
- **THEN** token 有效期 MUST 不超过 2 分钟

### Requirement: Print readiness protocol

系统 SHALL 在 print route 中实现 PrintReadyRegistry，确保图片、图表和字体全部就绪后 Playwright 才触发打印。

#### Scenario: All resources ready
- **WHEN** 所有图片已解码、所有图表已静态化、所有字体已加载
- **THEN** `window.__REPORT_PRINT_READY__` MUST 为 `true`

#### Scenario: No images or charts
- **WHEN** 报告不包含图片和图表
- **THEN** `window.__REPORT_PRINT_READY__` MUST 在所有文本渲染完成后立即设为 `true`

#### Scenario: Readiness is not set unconditionally in finally
- **WHEN** print-data 请求失败、schema 校验失败、图片解码失败或字体加载失败
- **THEN** 系统 MUST NOT 在 `finally` 块中无条件设置 `__REPORT_PRINT_READY__ = true`
- **AND** 系统 MUST 设置 `window.__REPORT_PRINT_ERROR__ = { code, message }`
- **AND** Playwright 观察到 `__REPORT_PRINT_ERROR__` 或 ready 超时时 MUST 使导出失败

#### Scenario: Layout overflow blocks export
- **WHEN** 任一 `.print-page` 内容溢出（scrollHeight > clientHeight + 2）
- **THEN** 系统 MUST 设置 `window.__REPORT_PRINT_ERROR__ = { code: "PRINT_LAYOUT_OVERFLOW", pageNumber }`
- **AND** MUST NOT 通过 `overflow: hidden` 静默截断内容
- **AND** 导出 MUST 失败并明确指出溢出页

#### Scenario: Timeout must fail export
- **WHEN** 资源加载超过 30 秒仍未就绪
- **THEN** 系统 MUST NOT 强制设置 `__REPORT_PRINT_READY__ = true`
- **AND** 系统 MUST 设置 `window.__REPORT_PRINT_ERROR__ = { code: "PRINT_READY_TIMEOUT", ... }`
- **AND** 导出 MUST 中止并标记为失败（`pdf_status = "export_failed"`）

### Requirement: Render result validation

系统 SHALL 在 Playwright 渲染完成后校验打印页真实就绪，未就绪或页面出错时中止导出，不得产出内容错误的 PDF。

#### Scenario: Page not ready fails export
- **WHEN** Playwright 等待 `window.__REPORT_PRINT_READY__ === true` 超时
- **THEN** 系统 MUST 中止导出，不调用 `page.pdf()`
- **AND** 导出结果 MUST 为 `pdf_status = "export_failed"` 且 `pdf_error` 含可读信息

#### Scenario: Page error fails export
- **WHEN** 页面设置了 `window.__REPORT_PRINT_ERROR__`（如 PRINT_DATA_LOAD_FAILED、PRINT_READY_TIMEOUT、PRINT_LAYOUT_OVERFLOW）
- **THEN** 系统 MUST 以该错误码中止导出，不调用 `page.pdf()`
- **AND** `pdf_error` MUST 透传页面错误信息

#### Scenario: Redirected print route fails export
- **WHEN** Playwright 打开 print 路由后页面被重定向离开（如跳转到 `/login`）
- **THEN** 系统 MUST 检测到目标 URL 不在 print 路由
- **AND** 中止导出并标记 `export_failed`，不得将非报告页面作为 PDF 输出

### Requirement: Demo mode print data channel

系统 SHALL 保证 `VITE_API_BASE_URL` 未配置（demo 模式）时打印页仍能获取 print-data 并成功生成报告 PDF。

#### Scenario: Demo mode export succeeds
- **WHEN** 本地开发环境未配置 `VITE_API_BASE_URL`（`demoMode = true`）且用户请求 PDF 导出
- **THEN** 打印页 MUST 能获取 `/api/v1/internal/sessions/{session_id}/report/print-data` 数据
- **AND** `__REPORT_PRINT_READY__` MUST 正常置位
- **AND** 生成的 PDF MUST 为报告五页内容而非错误页或应用首页

### Requirement: Radar chart is staticized in print mode

系统 SHALL 在 print mode 下将 ECharts 雷达图从 canvas 转为静态 PNG 图片。

#### Scenario: Print mode converts chart
- **WHEN** `ReportRadarChart` 收到 `printMode=true` prop
- **THEN** 组件 MUST 在渲染完成后调用 `chart.getDataURL({ type: 'png', pixelRatio: 2 })` 替换 canvas 为 `<img>`
- **THEN** PDF 中的雷达图 MUST 为静态 PNG，非 canvas

### Requirement: Concurrent export returns 409

系统 SHALL 防止同一份报告被并发导出。

#### Scenario: Export while exporting
- **WHEN** 报告 `pdf_status = "exporting"` 时收到新的导出请求
- **THEN** 系统 MUST 返回 409 Conflict

#### Scenario: Re-export allowed
- **WHEN** `pdf_status = "exported"` 且 `force=true`
- **THEN** 系统 MUST 重新生成 PDF 并将 `pdf_version` 递增

### Requirement: PDF status tracking

系统 SHALL 跟踪每份报告的 PDF 导出状态，包含状态值、路径、版本号和错误信息。

#### Scenario: Status updated after export
- **WHEN** PDF 成功生成
- **THEN** `pdf_status` MUST 为 `"exported"`，`pdf_path` 和 `pdf_exported_at` 已写入
- **WHEN** PDF 生成失败
- **THEN** `pdf_status` MUST 为 `"export_failed"`，`pdf_error` 包含可读错误信息

### Requirement: save_bytes is awaited

`PdfExportService.export_report_pdf` SHALL 在调用 `StorageService.save_bytes` 时使用 `await`（方法本身已为 `async def`，不需要改签名）。

#### Scenario: save_bytes call is awaited

- **WHEN** `export_report_pdf` 调用 `self.storage.save_bytes(...)`
- **THEN** 调用 MUST 使用 `await` 关键字
- **THEN** 返回值 MUST 为 dict 而非 coroutine

### Requirement: Report API returns unified pdf_url

所有 PDF 导出端点返回的 `pdf_url` SHALL 通过统一 builder 生成，确保首次导出和缓存命中返回相同的 URL 格式。

#### Scenario: pdf_url includes api_prefix

- **WHEN** PDF 导出成功
- **THEN** `pdf_url` MUST 以 `settings.api_prefix`（如 `/api/v1`）开头
- **THEN** `pdf_url` MUST 格式为 `{api_prefix}/sessions/{session_id}/report/pdf`

### Requirement: Report ownership derived from session

PDF 导出端点 SHALL 通过 `require_owned_session` 校验用户对 session 的访问权限，不依赖 `ReportMetadata` 的独立 owner 字段。

#### Scenario: Unauthorized session returns 404

- **WHEN** 用户请求不属于自己可访问 session 的 PDF 导出
- **THEN** 系统 MUST 返回 404（不泄露 session 是否存在）

#### Scenario: Internal print-data uses token auth

- **WHEN** Playwright 请求 internal print-data 端点
- **THEN** 系统 MUST 校验 `token` 参数的有效性、purpose 和过期时间
- **THEN** 系统 MUST 校验 token 绑定的 session_id 与 URL session_id 一致
- **THEN** 系统 MUST 校验 token 绑定的 report_id 与数据库 report.session_id 一致

### Requirement: Internal router is hidden from OpenAPI

internal 端点 SHALL 使用独立的 `APIRouter(include_in_schema=False)` 注册，不在 Swagger 文档中展示。

#### Scenario: Internal endpoints not in Swagger

- **WHEN** 开发者访问 `GET /docs`
- **THEN** internal 端点 MUST NOT 出现在 OpenAPI 文档中

### Requirement: Download endpoint checks PDF status before returning

`GET /sessions/{session_id}/report/pdf` SHALL 在返回 PDF 文件前检查 `pdf_status`，不处理时应返回结构化错误。

#### Scenario: PDF not yet exported returns 404

- **WHEN** pdf_status = `not_exported`
- **THEN** 系统 MUST 返回 404 且不返回 PDF 文件

#### Scenario: PDF export in progress returns 409

- **WHEN** pdf_status = `exporting`
- **THEN** 系统 MUST 返回 409，`detail.code` = `pdf_export_in_progress`

#### Scenario: PDF export failed returns 409

- **WHEN** pdf_status = `export_failed`
- **THEN** 系统 MUST 返回 409，`detail.code` = `pdf_export_failed`

#### Scenario: DB exported but file missing returns 500

- **WHEN** pdf_status = `exported` 但文件不存在
- **THEN** 系统 MUST 返回 500，`detail.code` = `pdf_artifact_missing`
