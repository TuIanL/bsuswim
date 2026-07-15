## MODIFIED Requirements

### Requirement: Development frontend port is 5174 (MODIFIED)

后端默认开发配置 SHALL 使用 `http://localhost:5174` 作为前端 base URL，与 Vite 固定端口一致。

#### Scenario: CORS origins include 5174 (MODIFIED)

- **WHEN** 后端在默认开发配置下启动
- **THEN** `cors_origins` MUST 包含 `http://localhost:5174` 和 `http://127.0.0.1:5174`
- **THEN** `cors_origins` MAY 同时保留 `http://localhost:5173` 和 `http://127.0.0.1:5173` 以兼容其他启动方式

#### Scenario: PDF render base URL uses 5174 (MODIFIED)

- **WHEN** Playwright 渲染 PDF
- **THEN** `pdf_render_base_url` MUST 默认为 `http://localhost:5174`

#### Scenario: Frontend base URL uses 5174 (MODIFIED)

- **WHEN** 后端生成前端链接
- **THEN** `frontend_base_url` MUST 默认为 `http://localhost:5174`
