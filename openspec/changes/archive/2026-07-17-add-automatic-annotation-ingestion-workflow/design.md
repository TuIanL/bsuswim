## Context

当前系统已具备完整的标注上传 → 解析 → 标准化 → 质量验证能力，但存在以下几个问题导致用户无法顺畅完成从文件到分析输入的流程：

**API 分离**：上传和解析是两个独立请求。前端上传后不调用 parse，页面停在"文件已上传"状态。

**状态不可恢复**：`AnnotationFileListItem` 只包含原始文件元数据，不含 `normalized_annotation_id`、`quality_status` 或 `analysis_readiness`。页面刷新后所有摄取结果丢失。

**ID 契约缺失**：前端存在将 `AnnotationFileListItem.id` 作为 `normalized_annotation_id` 传入分析提交的情况。后端在 ID 未指定时通过 revision 降序猜测标注，在多版本场景下可能选错。

**N+1 查询**：前端对 parsed 文件逐条调用 `getAnnotationDetail` 尝试读取 quality，但详情 schema 同样不含 quality，查询无效。

**前端缺 CVAT**：后端 `AnnotationSource` 已包含 `cvat`，但前端类型和下拉菜单没有此选项。

## Goals / Non-Goals

**Goals:**

- 用户通过一次操作完成上传 → 解析 → 质量检查 → readiness 计算
- 摄取结果可通过列表响应恢复，不依赖单次 HTTP 响应
- 前端明确选择 normalized annotation，不靠后端猜测
- 有候选标注但未选时后端明确拒绝，而非静默猜测
- 只有 invalid/parse_failed 标注时明确返回不可用，不静默退到 video-only
- 无任何标注时保留 video-only 兼容
- warnings 持久化到 NormalizedAnnotation，页面刷新不丢失
- CVAT 来源在前端可选

**Non-Goals:**

- 不新增指标计算、报告生成或 diagnostics
- 不改变 parser、normalizer、resolver、quality checker 的具体逻辑
- 不重构 AnalysisTask 执行器
- 不删除原有 upload / parse / validate API
- 不引入消息队列、异步 worker、WebSocket 或 SSE
- 不伪造服务器端分步骤进度
- 不新增数据库迁移或 SQL 列

## Decisions

### D1: 普通前端只使用 ingest 端点

用户界面不保留两套上传流程。当前"上传标注"按钮替换为"上传并处理标注"，调用 `POST .../annotations/ingest`。上传页面不提供"先上传后解析"的手动分步操作。

旧接口保留但仅用于：

| 接口 | 用途 |
|------|------|
| upload | API 调试、特殊文件先保存后补参数 |
| parse | parse_failed 文件重新解析 |
| validate | validator/profile 更新后重新检查 |

### D2: Ingest 请求与响应

```
POST /sessions/{session_id}/videos/{video_id}/annotations/ingest
Content-Type: multipart/form-data
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `file` | File | 是 | 标注文件 |
| `source` | string | 是 | cvat / kinovea 等 |
| `annotation_fps` | float | 否 | 标注时间基准 |
| `metadata` | JSON string | 否 | 原始文件元数据 |
| `parse_options` | JSON string | 否 | CVAT frame mapping 等解析选项 |

响应字段命名约定：

| 响应字段 | 语义 |
|----------|------|
| `revision` | NormalizedAnnotation.revision（ingest 主要产物） |
| `parse_summary` | 解析结果计数（ingest 同时包含文件和标注，用前缀区分的更清晰） |
| `file_version` | AnnotationFile.version（原始文件在该 source 下的版本） |

旧 parse endpoint 的 `summary` 字段保持不变，避免破坏已有调用方。

### D3: 编排服务与现有能力的关系

新增 `annotation_ingestion_service.py`，依次调用：

```
1. create_annotation() — 保存物理文件 + 创建 AnnotationFile
2. parse_annotation_file() — 解析 + upsert NormalizedAnnotation
3. 返回合并结果
```

编排服务不直接调用 route 函数，也不重复实现文件保存或解析逻辑。

### D4: 列表响应可恢复摄取状态

`AnnotationFileListItem` 扩展为：

```python
QualityStatus = Literal["valid", "warning", "invalid"]

class AnnotationFileListItem(BaseModel):
    id: int
    session_video_id: int
    source: AnnotationSource
    view_type: ViewType | None
    file_type: str | None
    version: int
    status: AnnotationFileStatus
    original_filename: str
    annotation_fps: float | None
    uploaded_at: datetime | None

    normalized_annotation_id: int | None = None
    normalized_revision: int | None = None
    quality_status: QualityStatus | None = None
    analysis_readiness: AnalysisReadiness | None = None
    parse_warnings: list[str] = Field(default_factory=list)
    parse_error: str | None = None
```

**查询必须使用 LEFT OUTER JOIN**：

```sql
AnnotationFile
LEFT OUTER JOIN NormalizedAnnotation
ON NormalizedAnnotation.annotation_file_id = AnnotationFile.id
```

未解析或 parse_failed 的文件必须保留在列表中。

### D5: analysis_readiness 共享化

将 `derive_analysis_readiness()` 从 `normalized_annotations.py` route 模块移至共享位置（如 `app/services/annotation_quality/readiness.py`），供以下位置复用：

- parse endpoint
- ingest endpoint
- validate endpoint
- annotation list 响应填充

### D6: Warnings 持久化到 annotation_metadata.parse

warnings 由 `parse_annotation_file()` 在 upsert 之前计算并写入 metadata：

```python
warnings = resolve_parse_warnings(...)
parse_metadata = {
    **metadata.get("parse", {}),
    "warnings": warnings,
    "parsed_at": utc_now_iso(),
}
metadata["parse"] = parse_metadata

# 再执行 NormalizedAnnotation upsert（metadata 已包含 parse 信息）
```

写入结构：

```json
{
  "parse": {
    "warnings": ["FRAME_MAPPING_UNVERIFIED"],
    "parsed_at": "2026-07-17T10:00:00Z"
  }
}
```

parser name/version 以在 metadata 其他位置存在，不在此重复。

规则：

- 在 upsert 之前完成 warnings 计算和 metadata 装配
- 重新解析时覆盖，不追加
- parse 失败时不覆盖上一次成功的 metadata
- 不涉及数据库迁移

### D7: 分析提交的三态判断

```python
all_annotations = query_side_view_annotations(session_id)

submittable = [
    ann for ann in all_annotations
    if ann.file_status == "parsed"
    and ann.quality_status in ("valid", "warning")
]

if payload.normalized_annotation_id is not None:
    annotation = resolve_explicit_annotation(
        payload.normalized_annotation_id
    )

elif submittable:
    raise AnnotationSelectionRequiredError(
        candidate_ids=[ann.id for ann in submittable]
    )

elif all_annotations:
    raise AnnotationInputUnavailableError(
        reason="NO_SUBMITTABLE_ANNOTATION"
    )

else:
    annotation = None  # 真正没有标注，允许 video-only
```

| 状态 | 行为 |
|------|------|
| 有 valid/warning 但未选 | `ANNOTATION_SELECTION_REQUIRED` (422) |
| 只有 invalid / parse_failed | `ANNOTATION_INPUT_UNAVAILABLE` (422) |
| 完全没有标注 | video-only 继续 |
| 明确传 invalid 标注 | 现有质量门禁阻断 |

候选查询限定 `SessionVideo.view_type = "side"`。

### D8: 前端状态模型

```typescript
type AnnotationWorkflowStage =
  | 'idle'
  | 'selected'
  | 'ingesting'
  | 'ready'
  | 'warning'
  | 'invalid'
  | 'failed'
```

点击"上传并处理标注"后立即设为 `ingesting`。同步请求返回后根据 `quality.status` 映射到 `ready` / `warning` / `invalid`，catch 时设为 `failed`。

### D9: 前端标注选择

一个侧面视频有多条标注时：

- 默认按 `uploaded_at DESC, id DESC` 选择 latest submittable
- `version` 是 source 本地版本号，不能作为跨 source 的新旧依据
- warning 标注可选，但提交前需确认
- invalid 标注不可选
- 提交时前端发送 `normalized_annotation_id` 和 `acknowledge_quality_warnings`
- 禁止将 `AnnotationFile.id` fallback 为 `normalized_annotation_id`

`selectedNormalizedAnnotationId` 保存在侧面 camera state 内。

### D10: parse_failed 重试路径

摄取失败但 `annotation_file_id` 已返回时：

- 页面保留该记录
- "重新解析"调用 `POST /annotations/{annotation_file_id}/parse`
- 成功后重新加载列表
- 不重新上传文件

### D11: 错误码领域前缀

```python
ANNOTATION_INGEST_UPLOAD_FAILED
ANNOTATION_INGEST_PARSE_FAILED
ANNOTATION_INGEST_INVALID_PARSE_OPTIONS
ANNOTATION_INGEST_UNSUPPORTED_SOURCE
ANNOTATION_SELECTION_REQUIRED
ANNOTATION_INPUT_UNAVAILABLE
```

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| ingest 端点可能逐渐废弃旧 upload | 保留旧接口但不暴露在普通 UI 中 |
| 删除 fallback 破坏无 ID 的集成调用 | 仅 session 有可提交标注时拒绝；无标注时保持 video-only |
| 只有 invalid 标注时不慎退回 video-only | 三态判断：明确区分"无标注""无可用标注""未选择" |
| 前端当前 quality_status 字段后端不返回 | 后端补上后前端保留现有声明 |
