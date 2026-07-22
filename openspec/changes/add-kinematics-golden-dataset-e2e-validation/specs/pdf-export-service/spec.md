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

### Requirement: PDF export uses frontend print route

系统 SHALL 使用 Playwright 打开前端专用 print route（非 Jinja2 后端模板）生成 PDF 报告。

#### Scenario: Export triggers frontend print

- **WHEN** 用户请求 PDF 导出
- **THEN** 系统 MUST 通过 Playwright 打开前端 `/reports/{sessionId}/print?token={token}` 路由进行渲染
- **THEN** 后端 MUST 不维护独立 Jinja2 报告模板

#### Scenario: Print route emits exactly five pages

- **WHEN** 系统为 `side_2d_kinematics_5page_v1` 报告导出 PDF
- **THEN** print route MUST 按 ReportData 的五个 sections 渲染五个 `.print-page`
- **AND** MUST NOT 额外渲染独立封面页
- **AND** 生成的 PDF 实际页数 MUST 严格等于 5
- **AND** 每页 MUST 包含对应 page semantic marker（ASCII 格式 `P{n} | {page_type}`）
- **AND** PDF 页序与标题 MUST 与 ReportData sections 一致
