## Why

commit `26f7c2a` 将 CVAT 骨架导入和后端管线推送到 GitHub 后，代码审计发现 4 个会直接阻断真实链路的硬问题：PostgreSQL 枚举缺 `cvat`、PDF 前后端路径不匹配、`save_bytes` 未 `await`、端口配置不一致。在进入下一个大 Change 之前，必须先修复这些阻断问题，使仓库达到可信的端到端可运行状态。

## What Changes

- **新增 migration**：`ALTER TYPE annotationsource ADD VALUE 'cvat'`，使 CVAT 文件可写入数据库
- **统一 PDF API 路径契约**：拆分独立 `report_exports` router，路径与前端请求一致
- **修复 `save_bytes` 缺少 await**：PDF 导出时 `self.storage.save_bytes(...)` 前补 `await`（方法本身已为 async，不需要改签名）
- **统一端口配置**：后端 CORS / base URL 与 Vite 5174 端口对齐
- **修复 ParseResponse quality 类型**：使用 v2 `AnnotationQualityReport` 替代 legacy `AnnotationQuality`，保留强类型校验
- **修复 revalidate profile 选择**：CVAT 标注使用 `side_technical_v1_cvat` profile
- **对齐唯一约束**：NormalizedAnnotation 删除冗余 `unique=True`，AnnotationMetric 补充 `__table_args__`
- **增加真实 route 测试**：通过 HTTP client 断言 API 路径、状态码和错误契约
- **增加 GitHub Actions CI**：在 clean checkout 上执行后端 import、migration、test、前端 build

## Capabilities

### New Capabilities

- `pdf-api-contract`：定义 PDF 导出相关的公共 API 路径、状态码和错误响应契约，与前端请求一致

### Modified Capabilities

- `pdf-export-service`：API 路径从 `/reports/sessions/{id}/...` 修正为 `/sessions/{id}/report/...`；`save_bytes()` 调用补 `await`；增加统一 `pdf_url` builder；`/report/pdf` 端点增加结构化状态错误响应
- `normalized-annotation-schema`：`AnnotationSource` 枚举增加 `cvat`，新增 migration 补齐 PostgreSQL enum
- `annotation-quality`：parse route 返回 v2 quality 时不再强制塞回 legacy 结构；revalidate 端点根据 `ann.source` 选择正确 profile
- `backend-platform-core`：默认端口从 5173 改为 5174（仅配置变更，非 breaking）

## Impact

- `backend/alembic/versions/`：新增 migration `20260714_0007_add_cvat_annotation_source.py`
- `backend/app/api/routes/report_exports.py`：新增文件，定义 public + internal 两个 router
- `backend/app/api/router.py`：注册 report_exports 路由
- `backend/app/services/pdf_export_service.py`：`save_bytes` 调用加 `await`，方法签名改为 async
- `backend/app/core/config.py`：CORS origins 和 base URL 端口改为 5174
- `backend/app/schemas/normalized_annotation.py`：ParseResponse quality 字段改为 `AnnotationQualityReport`
- `backend/app/services/annotation_quality/profile_resolver.py`：新增 profile 选择函数
- `backend/app/models/normalized_annotation.py`：删除 `annotation_file_id` 上冗余的 `unique=True`
- `backend/app/models/annotation_metric.py`：增加 `__table_args__` 唯一约束
- `backend/tests/`：增加 PDF route 集成测试、print token 测试、profile 测试
- `.github/workflows/`：新增 CI workflow
