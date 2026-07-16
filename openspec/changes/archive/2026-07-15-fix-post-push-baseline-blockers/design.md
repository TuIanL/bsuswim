## Context

commit `26f7c2a` 将 CVAT 骨架导入、annotation metrics 管线、PDF 导出和 Swim Report v1 推送到 GitHub。代码审计发现以下层面的阻断问题：

- **数据库层**：`AnnotationSource` Python 枚举含 `cvat`，但 PostgreSQL `annotationsource` 类型缺少该值，写入即报错
- **路由层**：PDF 相关端点实际路径为 `/api/v1/reports/sessions/{id}/...`，但前端请求 `/api/v1/sessions/{id}/report/...`
- **异步层**：`PdfExportService.export_report_pdf` 中 `self.storage.save_bytes(...)` 缺少 `await`，运行时得到 coroutine 而非 dict
- **配置层**：后端默认端口 5173 与 Vite 固定端口 5174 不匹配，导致 CORS 和 Playwright 渲染失败
- **序列化层**：ParseResponse 将 v2 quality 强制塞回 legacy `AnnotationQuality`，导致 `analysis_readiness` 与 `quality` 自相矛盾
- **profile 层**：`/validate` 端点硬编码 `side_technical_v1` profile，CVAT 标注应使用 `side_technical_v1_cvat`
- **模型层**：NormalizedAnnotation 重复声明唯一约束，AnnotationMetric 缺少模型级唯一约束

这些问题都在提交时未通过端到端场景验证暴露出来。

## Goals / Non-Goals

**Goals:**
- CVAT 标注文件可成功写入 PostgreSQL
- PDF 导出全链路（发起导出 → 查询状态 → 下载 PDF → 打印数据）路径正确且可运行
- 后端端口配置与前端一致，Playwright 可正常渲染
- ParseResponse 的 quality 字段反映真实 v2 状态
- 重新验证时使用与 parse 阶段一致的 profile
- SQLAlchemy model 与 migration 约束定义一致
- 增加 route 级集成测试覆盖以上场景
- 增加 GitHub Actions CI 门禁

**Non-Goals:**
- 不新增 CVAT XML parser 能力
- 不修改标注质量 v2 的校验规则本身
- 不修改 metrics engine 或 diagnostics engine 的计算逻辑
- 不新增 PDF 报告内容（版本列表、对比等）
- 不处理 frame mapping 从文件名解析帧号（单独修复）
- 不删除旧 frontend/ 目录（已在 `26f7c2a` 中删除）

## Decisions

### Decision 1：PDF API 路径 — 独立 report_exports router

**结论**：新增 `backend/app/api/routes/report_exports.py`，定义两个独立 `APIRouter`。

```python
public_router = APIRouter(tags=["report-exports"])
internal_router = APIRouter(prefix="/internal", tags=["internal-report-exports"])
```

总路由分别注册（不加 `/reports` 前缀）：

```python
api_router.include_router(report_exports.public_router)
api_router.include_router(report_exports.internal_router)
```

最终路径：

| 端点 | 路径 |
|------|------|
| 导出 PDF | `POST /sessions/{session_id}/report/export/pdf` |
| 下载 PDF | `GET /sessions/{session_id}/report/pdf` |
| 导出状态 | `GET /sessions/{session_id}/report/export/pdf/status` |
| 打印数据 | `GET /internal/sessions/{session_id}/report/print-data` |

**不选方案 B（搬进 sessions router）**：PDF 导出依赖 Playwright、PrintToken、StorageService，不属于 session 领域；sessions router 会膨胀。

**不选方案 C（前端适配 `/reports` 路径）**：会固化 `/reports/sessions/{id}/report/...` 这种重复路径，未来版本化更难扩展。

**理由**：一个文件、两个 router 既保持了文件级组织清晰，又让鉴权边界可读——public router 依赖 `get_current_user`，internal router 依赖 print token 校验。`internal_router` 注册时设置 `include_in_schema=False`，避免暴露在公共 OpenAPI 文档中。

#### 统一 pdf_url builder

当前首次导出和缓存命中返回的 `pdf_url` 路径不一致（分别缺 `/v1` 和有 `/v1`）。增加统一 builder：

```python
# app/services/reporting/pdf_url.py
def build_session_report_pdf_url(session_id: int) -> str:
    from app.core.config import get_settings
    settings = get_settings()
    return (
        f"{settings.api_prefix}"
        f"/sessions/{session_id}/report/pdf"
    )
```

所有 PDF 导出端点返回的 `pdf_url` 统一使用此函数生成。

### Decision 2：`/report/pdf` 端点错误契约

| 条件 | HTTP 状态 | `detail.code` |
|------|-----------|---------------|
| session 无权限 | 404 | `session_not_found` |
| session 无报告 | 404 | `report_not_found` |
| 从未导出 | 404 | `pdf_not_exported` |
| 正在导出 | 409 | `pdf_export_in_progress` |
| 上次失败 | 409 | `pdf_export_failed` |
| DB 已导出但文件丢失 | 500 | `pdf_artifact_missing` |
| DB 不存在 | 404 | `report_not_found` |

统一行为：不重定向，成功返回 `application/pdf`，失败返回 JSON `{ detail: { code, message, ... } }`。

### Decision 3：权限校验以 session 为唯一边界

`ReportMetadata` 不设独立 owner。当前数据库已存在 `uq_report_session` 唯一约束，一个 session 至多一条报告记录。公共端点通过两步获取：

```python
# 1. 校验 session 访问权限
session = require_owned_session(db, session_id=session_id, user_id=user_id)

# 2. 基于 uq_report_session 约束，查询唯一报告
from sqlalchemy import select
report = db.scalar(
    select(ReportMetadata).where(
        ReportMetadata.session_id == session_id
    )
)
```

`require_owned_session` 放在 repository 层（`app/repositories/training_session_repository.py`），不反向依赖 API router。

Internal print-data 端点不走 `require_owned_session`，改为 print token 鉴权 + token 与 URL session_id + report.session_id 三层一致性校验。

**未来报告版本化**时需另起 Change：移除 `uq_report_session`、增加 `version`/`is_current`/`superseded_at` 字段、定义 current report 选择规则。本 Change 不处理。

### Decision 4：CVAT enum migration

新增 Alembic migration（`20260714_0007_add_cvat_annotation_source.py`）：

```python
def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TYPE annotationsource "
            "ADD VALUE IF NOT EXISTS 'cvat'"
        )

def downgrade() -> None:
    # PostgreSQL 不支持安全移除 enum value。
    # 该 migration 是前向兼容的数据类型扩展，不可逆。
    pass
```

使用 `autocommit_block` 避免 PostgreSQL 禁止在事务内 ALTER ENUM 的限制。

**downgrade 明确 no-op**：PostgreSQL 不支持 `ALTER TYPE ... DROP VALUE`，移除前需确认 enum 未被任何行使用，否则必须重建数据类型。该 migration 是纯扩展、不破坏现有数据，因此 downgrade 不做操作。

### Decision 5：ParseResponse quality 使用 v2 AnnotationQualityReport

当前 `ParseResponse.quality` 是 legacy `AnnotationQuality` Pydantic model（认 `level` 字段），与 v2 validator 输出的 `AnnotationQualityReport`（认 `status` 字段）不兼容。

不再用 legacy 类型降级，改用仓库中已有的 `AnnotationQualityReport`：

```python
from app.schemas.quality import AnnotationQualityReport

class ParseResponse(BaseModel):
    ...
    quality: AnnotationQualityReport
```

route 层直接 `AnnotationQualityReport.model_validate(ann.quality)`，保留强类型校验和 OpenAPI 文档。

Legacy `AnnotationQuality` 在 parse 场景中不再使用；未来删除 legacy 类型是一个独立 Change。

### Decision 6：Profile resolver 按 source 选择

parse 阶段（NormalizedAnnotation 创建前）和 validate 阶段都需要选择 profile。因此参数不能是 ORM 对象，改为接受 source 值：

```python
# app/services/annotation_quality/profile_resolver.py

def resolve_quality_profile_id(
    source: str | AnnotationSource,
) -> str:
    value = getattr(source, "value", source)
    if value == AnnotationSource.CVAT.value:
        return "side_technical_v1_cvat"
    return "side_technical_v1"
```

调用方式：

```python
# parse（在创建 ORM 对象前）
profile_id = resolve_quality_profile_id(source_value)

# revalidate
profile_id = resolve_quality_profile_id(ann.source)
```

位置放在 `app/services/annotation_quality/profile_resolver.py`，不属于 normalized annotation service 领域。

### Decision 7：唯一约束对齐

- `NormalizedAnnotation.__table_args__`：保留 `UniqueConstraint("annotation_file_id", ...)`，删除 `annotation_file_id` 列上的 `unique=True`
- `AnnotationMetric`：增加 `__table_args__` 含 `UniqueConstraint("normalized_annotation_id", "calculator", "calculator_version", name="uq_annotation_metrics_calc")`

### Decision 8：测试分层

| 测试类型 | 目标 | 方式 |
|----------|------|------|
| Helper 单元测试 | `_pdf_state_error` | `pytest.raises(HTTPException)` |
| Route 集成测试 | PDF 端点路径与状态码 | `TestClient` + `response.status_code` + `response.json()["detail"]["code"]` |
| Print token 单元测试 | 生成/校验/过期 | 直接调用 service 函数 |
| Profile 单元测试 | profile 选择逻辑 | 直接调用 resolver |
| DB migration 测试 | 空库 upgrade head + 增量升级 0006→0007 | `alembic upgrade head` + 从 0006 升级到 0007 + `SELECT unnest(enum_range(NULL::annotationsource))` |
| CI 串联测试 | 完整基线 | `scripts/verify_baseline.sh` |

### Decision 9：CI 门禁

新增 GitHub Actions workflow（`ci.yml`），在 push/PR 时执行：

1. 后端 `compileall` + import check
2. 空 PostgreSQL 数据库 `alembic upgrade head`
3. `pytest -q`
4. 前端 `npm ci` + `npm run build`

整个 workflow 使用 clean checkout，不依赖本地遗留文件。

## Risks / Trade-offs

- **[Risk] `ALTER TYPE ... ADD VALUE` 在事务内执行**：PostgreSQL 不允许在显式事务块内 ALTER ENUM。Alembic 默认每个 migration 运行在事务中。需确保 migration 使用 `op.execute()` 在事务外执行或 Alembic 的 `transaction=False` 模式。
  → **Mitigation**：使用 Alembic 的 `with op.get_context().autocommit_block():` 包装 `op.execute()`，避免事务冲突。

- **[Risk] async 调用链缺少 await**：当前 `export_report_pdf` 和 route handler 已均为 `async def`，唯一问题是 `save_bytes()` 调用前缺少 `await`。本 Change 仅补这一个 `await`，不扩展异步边界。
  → **Mitigation**：增加 `AsyncMock` 回归测试，`assert_awaited_once_with(...)`。

- **[Risk] Internal route 暴露在公开 OpenAPI**：`internal_router` 默认会被 Swagger 文档收录，可能被误认为公共 API。
  → **Mitigation**：`internal_router` 注册时设置 `include_in_schema=False`，仍然是可访问的 token-auth endpoint，但不在公开文档中显示。

- **[Trade-off] 不修复 frame mapping 文件名解析**：CVAT 的 frame mapping 时间戳仍为 None，部分时间依赖指标标记为 blocked。
  → **接受**：这是指标启用的优化，不是阻断。P0.1 只修复阻断问题。
