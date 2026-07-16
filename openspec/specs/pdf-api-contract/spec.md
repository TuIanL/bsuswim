## ADDED Requirements

### Requirement: PDF export uses session-level public API path

PDF 导出相关 API SHALL 使用 `/sessions/{session_id}/report/` 作为公共路径前缀，匹配前端现有请求契约。

#### Scenario: Export by session

- **WHEN** 前端发起 PDF 导出请求
- **THEN** 系统 MUST 接受 `POST /sessions/{session_id}/report/export/pdf`

#### Scenario: Download by session

- **WHEN** 前端发起 PDF 下载请求
- **THEN** 系统 MUST 接受 `GET /sessions/{session_id}/report/pdf`

#### Scenario: Status by session

- **WHEN** 前端轮询 PDF 导出状态
- **THEN** 系统 MUST 接受 `GET /sessions/{session_id}/report/export/pdf/status`

### Requirement: Internal print-data API uses /internal prefix

Playwright 渲染使用的 print-data API SHALL 使用 `/internal/` 前缀，与公共 API 路径隔离。

#### Scenario: Print data by session

- **WHEN** Playwright 无头浏览器请求打印数据
- **THEN** 系统 MUST 接受 `GET /internal/sessions/{session_id}/report/print-data`，通过 `token` query 参数鉴权

### Requirement: PDF download has structured error responses

`GET /sessions/{session_id}/report/pdf` SHALL 根据 PDF 生成状态返回结构化错误响应，不返回重定向。

#### Scenario: Session has no report

- **WHEN** session 不存在或不可访问
- **THEN** 系统 MUST 返回 404，`detail.code` = `session_not_found`

#### Scenario: Session has no report metadata

- **WHEN** session 存在但尚无报告
- **THEN** 系统 MUST 返回 404，`detail.code` = `report_not_found`

#### Scenario: PDF never exported

- **WHEN** pdf_status = `not_exported`
- **THEN** 系统 MUST 返回 404，`detail.code` = `pdf_not_exported`

#### Scenario: PDF export in progress

- **WHEN** pdf_status = `exporting`
- **THEN** 系统 MUST 返回 409，`detail.code` = `pdf_export_in_progress`

#### Scenario: PDF export previously failed

- **WHEN** pdf_status = `export_failed`
- **THEN** 系统 MUST 返回 409，`detail.code` = `pdf_export_failed`

#### Scenario: DB exported but file missing

- **WHEN** pdf_status = `exported` 且 `pdf_path` 不为空但文件不存在
- **THEN** 系统 MUST 返回 500，`detail.code` = `pdf_artifact_missing`，并更新 DB 状态为 `export_failed`

#### Scenario: DB exported but pdf_path is null

- **WHEN** pdf_status = `exported` 但 `pdf_path` 为空
- **THEN** 系统 MUST 返回 500，`detail.code` = `pdf_artifact_missing`，而非 404 `pdf_not_exported`

### Requirement: Old PDF routes return 404

重构后，原 `/reports/sessions/{session_id}/report/export/pdf` 等旧路径 SHALL 不再生效。

#### Scenario: Old path returns 404

- **WHEN** 客户端请求 `POST /api/v1/reports/sessions/{session_id}/report/export/pdf`
- **THEN** 系统 MUST 返回 404

### Requirement: Route tests use HTTP client

PDF API 集成测试 SHALL 通过 `TestClient` 断言 `response.status_code` 与 `response.json()["detail"]["code"]`，不直接捕获 `HTTPException`。

#### Scenario: Route test asserts status and error code

- **WHEN** 集成测试请求 PDF API 端点
- **THEN** 测试 MUST 通过 `response.status_code` 断言 HTTP 状态码
- **THEN** 测试 MUST 通过 `response.json()["detail"]["code"]` 断言错误类型

### Requirement: Concurrent export returns 409

系统 SHALL 防止同一 session 的报告被并发导出。

#### Scenario: Export while already exporting

- **WHEN** 报告 `pdf_status = "exporting"` 时收到新的导出请求
- **THEN** 系统 MUST 返回 409 Conflict，`detail.code` = `pdf_export_in_progress`

#### Scenario: Re-export allowed after completion

- **WHEN** `pdf_status = "exported"` 且 `force=true`
- **THEN** 系统 MUST 重新生成 PDF 并将 `pdf_version` 递增
