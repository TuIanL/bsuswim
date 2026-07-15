## MODIFIED Requirements

### Requirement: Export API uses session-level key (MODIFIED)

PDF 导出相关 API SHALL 使用 `session_id` 作为公开查找键。**公共 API 路径从 `/api/sessions/{session_id}/report/export/pdf` 模式正式定为 `/sessions/{session_id}/report/export/pdf`（无 `/reports` 前缀）**。差异化 endpoints 定义移至 `pdf-api-contract` spec。

### Requirement: Export API common router registration (ADDED)

PDF 导出路由 SHALL 注册在 API 根 router 上，不使用 `/reports` 前缀。

#### Scenario: Route registered without reports prefix

- **WHEN** 后端应用启动
- **THEN** PDF 导出相关路由 MUST 可通过 `/api/v1/sessions/{session_id}/report/export/pdf` 访问

### Requirement: save_bytes is awaited (ADDED)

`PdfExportService.export_report_pdf` SHALL 在调用 `StorageService.save_bytes` 时使用 `await`（方法本身已为 `async def`，不需要改签名）。

#### Scenario: save_bytes call is awaited

- **WHEN** `export_report_pdf` 调用 `self.storage.save_bytes(...)`
- **THEN** 调用 MUST 使用 `await` 关键字
- **THEN** 返回值 MUST 为 dict 而非 coroutine

#### Scenario: AsyncMock regression test

- **WHEN** 单元测试 mock `StorageService.save_bytes` 为 `AsyncMock`
- **THEN** 测试 MUST `assert_awaited_once_with(...)`

### Requirement: Report API returns unified pdf_url (ADDED)

所有 PDF 导出端点返回的 `pdf_url` SHALL 通过统一 builder 生成，确保首次导出和缓存命中返回相同的 URL 格式。

#### Scenario: pdf_url includes api_prefix

- **WHEN** PDF 导出成功
- **THEN** `pdf_url` MUST 以 `settings.api_prefix`（如 `/api/v1`）开头
- **THEN** `pdf_url` MUST 格式为 `{api_prefix}/sessions/{session_id}/report/pdf`

### Requirement: Report ownership derived from session (ADDED)

PDF 导出端点 SHALL 通过 `require_owned_session` 校验用户对 session 的访问权限，不依赖 `ReportMetadata` 的独立 owner 字段。

#### Scenario: Unauthorized session returns 404

- **WHEN** 用户请求不属于自己可访问 session 的 PDF 导出
- **THEN** 系统 MUST 返回 404（不泄露 session 是否存在）

#### Scenario: Internal print-data uses token auth

- **WHEN** Playwright 请求 internal print-data 端点
- **THEN** 系统 MUST 校验 `token` 参数的有效性、purpose 和过期时间
- **THEN** 系统 MUST 校验 token 绑定的 session_id 与 URL session_id 一致
- **THEN** 系统 MUST 校验 token 绑定的 report_id 与数据库 report.session_id 一致

### Requirement: Internal router is hidden from OpenAPI (ADDED)

internal 端点 SHALL 使用独立的 `APIRouter(include_in_schema=False)` 注册，不在 Swagger 文档中展示。

#### Scenario: Internal endpoints not in Swagger

- **WHEN** 开发者访问 `GET /docs`
- **THEN** internal 端点 MUST NOT 出现在 OpenAPI 文档中

### Requirement: Print data response wraps adapter output (ADDED)

`GET /internal/sessions/{session_id}/report/print-data` SHALL 返回包含 `adapter`（reportAdapter 输出）和 `resources`（printReadyRegistry 状态）的 JSON 响应。

#### Scenario: Print data returns adapter output

- **WHEN** token 有效且 session 有报告
- **THEN** 响应 MUST 包含 `adapter` 字段，内容为 reportAdapter 生成的 ViewModel
- **THEN** 响应 MUST 包含 `resources` 字段，内容为 printReadyRegistry 状态

### Requirement: Download endpoint checks PDF status before returning (ADDED)

`GET /sessions/{session_id}/report/pdf` SHALL 在返回 PDF 文件前检查 `pdf_status`，不处理时应返回结构化错误。

#### Scenario: PDF not yet exported returns 404

- **WHEN** pdf_status = `not_exported`
- **THEN** 系统 MUST 返回 404 且不返回 PDF 文件
