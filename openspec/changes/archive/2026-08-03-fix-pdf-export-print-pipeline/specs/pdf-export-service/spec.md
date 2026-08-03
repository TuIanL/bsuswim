# pdf-export-service (delta)

## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: Demo mode print data channel

系统 SHALL 保证 `VITE_API_BASE_URL` 未配置（demo 模式）时打印页仍能获取 print-data 并成功生成报告 PDF。

#### Scenario: Demo mode export succeeds

- **WHEN** 本地开发环境未配置 `VITE_API_BASE_URL`（`demoMode = true`）且用户请求 PDF 导出
- **THEN** 打印页 MUST 能获取 `/api/v1/internal/sessions/{session_id}/report/print-data` 数据
- **AND** `__REPORT_PRINT_READY__` MUST 正常置位
- **AND** 生成的 PDF MUST 为报告五页内容而非错误页或应用首页
