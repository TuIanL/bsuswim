## Why

当前原始标注上传、解析、质量检查和标准化标注存储是四个分离的接口和步骤。用户上传XML后页面只显示"文件已上传"，不会自动触发解析；页面刷新后丢失所有摄取结果（normalized_annotation_id、quality状态、analysis_readiness）；前端提交分析时存在将AnnotationFile.id作为normalized_annotation_id传入的错误，且后端在未指定ID时会通过revision猜测一条标注而非要求用户明确选择。

## What Changes

- 新增高层标注摄取端点 `POST /sessions/{session_id}/videos/{video_id}/annotations/ingest`，一站式完成上传、解析、质量检查和readiness计算
- 扩展 `AnnotationFileListItem` 响应：增加 `normalized_annotation_id`、`revision`、`quality_status`、`analysis_readiness`、`parse_warnings`
- 持久化 parse warnings 到 `NormalizedAnnotation.annotation_metadata.parse`
- 将 `derive_analysis_readiness` 从 route 模块移至共享位置，供 ingest、parse、validate、list 复用
- 前端普通用户流程只使用 ingest 端点，不再展示 upload + parse 双按钮流程
- 前端增加 CVAT 来源选项
- 前端实现标注选择状态，提交分析时明确传递 `normalized_annotation_id`
- 分析提交后端三态判断：
  - 有 valid/warning 标注但未选 ID → 422 `ANNOTATION_SELECTION_REQUIRED`
  - 只有 invalid/parse_failed 标注 → 422 `ANNOTATION_INPUT_UNAVAILABLE`
  - 完全没有标注 → video-only 兼容
- 候选查询限定 `SessionVideo.view_type = "side"`
- 默认标注选择按 `uploaded_at DESC, id DESC`，`version` 不作为跨 source 排序键
- 列表查询使用 `LEFT OUTER JOIN`，未解析和 parse_failed 文件必须保留在列表中
- 删除前端对 parsed 文件的逐条 `getAnnotationDetail` N+1 查询
- 保留 upload、parse、validate 接口作为调试/重试/API入口

## Capabilities

### New Capabilities

- `automatic-annotation-ingestion`: 系统通过一次 API 调用完成原始标注上传、解析、质量检查和 readiness 计算，摄取结果可通过列表响应恢复

### Modified Capabilities

- `annotation-file-persistence`: AnnotationFileListItem 扩展响应字段
- `normalized-annotation-schema`: parse warnings 持久化到 annotation_metadata
- `backend-platform-core`: 新增 ingestion route 和 service
- `session-analysis-submission`: 分析提交不再自动选择标注，有候选时强制指定

## Impact

- `backend/app/api/routes/annotations.py` — 扩展 GET list 响应
- `backend/app/schemas/annotation.py` — 扩展 AnnotationFileListItem
- `backend/app/services/annotation_ingestion_service.py` — 新增
- `backend/app/api/routes/normalized_annotations.py` — 共享 readiness
- `backend/app/services/analysis_service.py` — 三态判断取代 fallback
- `backend/app/api/routes/analysis.py` — 异常→HTTP 映射（AnnotationSelectionRequiredError → 422, AnnotationInputUnavailableError → 422）
- `backend/app/services/normalized_annotation_service.py` — warnings 持久化（metadata 装配提前到 upsert 之前）
- `frontend-vue/src/types.ts` — 扩展类型
- `frontend-vue/src/services/api.ts` — 新增 ingest 调用
- `frontend-vue/src/views/SessionUploadView.vue` — 替换按钮、状态模型、选择逻辑
- 不修改 parser、normalizer、resolver、quality checker、metrics、diagnostics、report
