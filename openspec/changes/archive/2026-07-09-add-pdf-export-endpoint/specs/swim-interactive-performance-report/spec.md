## MODIFIED Requirements

### Requirement: PDF export remains future capability

报告 SHALL 支持将 HTML 报告内容导出为 PDF，由后端通过 Playwright 渲染前端 print route 生成，并提供下载入口。

#### Scenario: User exports report to PDF
- **WHEN** 用户点击"导出 PDF"按钮且报告 `report_data` 已就绪
- **THEN** 系统 MUST 调用 `POST /api/sessions/{session_id}/report/export/pdf`，返回可下载的 PDF URL

#### Scenario: User downloads exported PDF
- **WHEN** 用户点击"下载 PDF"按钮
- **THEN** 系统 MUST 通过 `GET /api/sessions/{session_id}/report/pdf` 返回 PDF 文件

#### Scenario: PDF export status is tracked
- **WHEN** PDF 正在导出或已导出/失败
- **THEN** 系统 MUST 通过 `GET /api/sessions/{session_id}/report/export/pdf/status` 返回当前状态、时间戳和错误信息

#### Scenario: Report uses frontend print route
- **WHEN** 后端 Playwright 需要渲染报告
- **THEN** 系统 MUST 使用前端专用 `/reports/{sessionId}/print` 路由，而非后端 Jinja2 模板

## ADDED Requirements

### Requirement: Report print route

系统 SHALL 提供前端专用 print route，复用现有 section-based 报告渲染组件。

#### Scenario: Print page uses existing renderer
- **WHEN** 用户或 Playwright 访问 `/reports/{sessionId}/print`
- **THEN** 系统 MUST 使用同一套 `ReportSectionRenderer` / `ModuleSection` / `ReportRadarChart` 组件渲染
- **THEN** 页面 MUST 应用打印专用 CSS（A4 横版尺寸、隐藏交互元素）

#### Scenario: Print route signals readiness
- **WHEN** print route 加载完毕且所有资源（图片、图表、字体）就绪
- **THEN** 页面 MUST 设置 `window.__REPORT_PRINT_READY__ = true`
