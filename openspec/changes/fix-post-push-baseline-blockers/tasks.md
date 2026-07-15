## 1. PostgreSQL CVAT 枚举 migration

- [x] 1.1 创建 migration `20260714_0007_add_cvat_annotation_source.py`，使用 `autocommit_block` 执行 `ALTER TYPE annotationsource ADD VALUE IF NOT EXISTS 'cvat'`；downgrade 为 no-op（PostgreSQL 不支持安全移除 enum value）
- [x] 1.2 空数据库执行 `alembic upgrade head` 验证（通过）
- [x] 1.3 路径 B：从 0006 升级到 0007，模拟现有数据库真实升级（通过）
- [x] 1.4 执行 `SELECT unnest(enum_range(NULL::annotationsource))` 断言结果包含 `cvat`（通过）
- [ ] 1.5/pre-existing `alembic check` 失败（索引命名不一致，非本 Change 引入，需独立修复）

## 2. PDF API 路由重构

- [x] 2.1 新增 `backend/app/api/routes/report_exports.py`，定义 `public_router` 和 `internal_router`
- [x] 2.2 将 `reports.py` 中的 PDF export/download/status/print-data 端点迁移到 `report_exports.py`
- [x] 2.3 在 `router.py` 中注册 `report_exports.public_router` 和 `report_exports.internal_router`（不加 `/reports` 前缀，`internal_router` 设置 `include_in_schema=False`）
- [x] 2.4 在 `PdfExportService.export_report_pdf` 中将 `self.storage.save_bytes(...)` 改为 `await self.storage.save_bytes(...)`（方法本身已为 async，不需要改签名）
- [x] 2.5 增加 `AsyncMock` 回归测试，`assert_awaited_once_with(...)`
- [x] 2.6 实现 `_pdf_state_error` helper（根据 pdf_status 返回结构化错误）
- [x] 2.7 实现 `require_owned_session`（放在 `app/repositories/training_session_repository.py`）
- [x] 2.8 实现 `_resolve_current_owned_report`（组合权限校验 + 报告查询）
- [x] 2.9 实现 internal print-data 端点的 token 三层校验（token → session_id → report.session_id）
- [x] 2.10 GET `/report/pdf` 端点整合 `_pdf_state_error` + FileResponse
- [x] 2.11 实现 `build_session_report_pdf_url(session_id)`，所有 PDF 响应统一调用
- [x] 2.12 验证首次导出和复用已有 PDF 返回相同 `pdf_url`（已通过 `build_session_report_pdf_url` 统一 builder 确保）
- [x] 2.13 Route 集成测试验证旧路径 `POST /api/v1/reports/sessions/{id}/report/export/pdf` 返回 404（已通过 mock DB 测试覆盖）

## 3. 端口配置统一

- [x] 3.1 修改 `backend/app/core/config.py`：CORS origins 和 base URLs 默认端口改为 5174（保留 5173 兼容）

## 4. ParseResponse quality 修复

- [x] 4.1 修改 `ParseResponse.quality` 字段类型为 `AnnotationQualityReport`（已有的 v2 Pydantic model）
- [x] 4.2 更新 parse route 中的装配逻辑，使用 `normalize_quality_payload(ann.quality)`（兼容 v1/v2）
- [x] 4.3 验证 `analysis_readiness` 与 `quality.status` 不矛盾

## 5. 统一 profile 选择

- [x] 5.1 新增 `app/services/annotation_quality/profile_resolver.py`，实现 `resolve_quality_profile_id(source)`（接受 `str | AnnotationSource`）
- [x] 5.2 parse service 使用 `resolve_quality_profile_id(source_value)`
- [x] 5.3 revalidate route 使用 `resolve_quality_profile_id(ann.source)`（替换硬编码 `side_technical_v1`）

## 6. 对齐唯一约束

- [x] 6.1 `NormalizedAnnotation` 模型：删除 `annotation_file_id` 列上的 `unique=True`，保留 `__table_args__` 中的 `UniqueConstraint`
- [x] 6.2 `AnnotationMetric` 模型：在 `__table_args__` 中增加 `UniqueConstraint("normalized_annotation_id", "calculator", "calculator_version", name="uq_annotation_metrics_calc")`
- [ ] 6.3/pre-existing `alembic check` 确认无漂移（索引命名漂移为预存问题，非本 Change 引入）

## 7. 测试

- [x] 7.1 `_pdf_state_error` helper 单元测试：`not_exported`/`exporting`/`export_failed`/`exported + pdf_path=null`（通过 `pytest.raises(HTTPException)` 断言）
- [x] 7.2 PDF route 集成测试（39 个测试覆盖 export/download/status/print-data 全场景）
- [x] 7.2.1 全覆盖（session_not_found、report_not_found、pdf_not_exported、pdf_export_in_progress、pdf_export_failed、pdf_artifact_missing、正常下载）
- [x] 7.2.2 覆盖 exported + pdf_path=null → 500 pdf_artifact_missing
- [x] 7.2.3 旧路径 404 验证（mock DB，已添加）
- [x] 7.3 print token 生成/校验/过期单元测试（已有）
- [x] 7.4 `resolve_quality_profile_id` 单元测试（cvat → CVAT profile、kinovea → default profile、未知值 → default profile）
- [x] 7.5 验证 `pytest -q` 全部通过（218 passed, 1 skipped - 含数据库集成测试）

## 8. CI 门禁

- [x] 8.1 新增 `.github/workflows/ci.yml`：在 push/PR 时执行
- [x] 8.2 CI steps：checkout → Python 环境 → compileall + import check → alembic upgrade head → pytest → Node 环境 → npm ci → npm run build
- [ ] 8.3 验证 CI 在 push 后成功运行（需要推送后查看 Actions）

## 9. 最终验证

- [ ] 9.1 在第二个全新 clone 中执行完整验证流程
- [ ] 9.2 确认 OpenSpec strict validation 通过
