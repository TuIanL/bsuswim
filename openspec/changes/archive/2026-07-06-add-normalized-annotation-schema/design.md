## Context

当前系统有一条分析链路：`training_session + session_videos → build_model_request_payload() → model_service → analysis_results → report_metadata`。`analysis_results` 同时存储观测数据（keypoint_frames、phases）和计算结果（metrics、diagnostics），导致输入层与输出层耦合。Change #1（`add-annotation-file-persistence`）已建立 `annotation_files` 表和 `session_video_id` 引用规范。

本 change 在 `annotation_files` 和 `analysis_results` 之间插入标准化观测层 `normalized_annotations`，使后续 metrics engine 和 diagnostics engine 只依赖统一格式，不绑定任何具体标注工具（Kinovea、Dartfish、AI 姿态、人工 JSON）。

## Goals / Non-Goals

**Goals:**
- 新增 `normalized_annotations` 表，使用 `session_video_id` 作为唯一归属引用，与 Change #1 规范一致
- 定义 `swim-annotation.v1` JSON schema，标准化 events、keypoint_frames、trajectories、manual_tags、scale、coordinate_system、quality 子结构
- 实现 annotation quality checker，根据数据完整性生成 quality.level（good / warning / error）
- 提供创建、查询、列表标准化标注的 API
- 提供 parse endpoint 骨架，联动更新 `annotation_files.status`
- `annotation_file_id` 可空，支持 manual JSON 和 AI pose 直出等无源文件场景

**Non-Goals:**
- 不实现 Kinovea CSV parser（拆到 Change 2.5）
- 不修改 `analysis_results` 表结构
- 不实现 metrics engine 或 diagnostics engine
- 不强制迁移现有 model_service mock 链路
- 不逐帧存储全身关键点（JSONB 聚合存储）

## Decisions

### Decision 1: `session_video_id` 作为唯一归属引用

**选择**：`normalized_annotations.session_video_id → session_videos.id`（单一外键）

**替代方案**：`session_id + video_file_id + camera_view` 三字段方案（原始方案）

**理由**：Change #1 已建立 `session_videos` 作为 session-video 关系的标准表达，`camera_view` 已存在于 `session_videos.view_type`。重复保存会造成一致性问题。标注归属应通过 `session_videos` 推导。

### Decision 2: parse endpoint 从 `annotation_file.session_video_id` 推导归属

**选择**：`POST /api/annotations/{annotation_file_id}/parse` 不接受客户端提供的 `session_video_id`，服务端通过 `annotation_files.session_video_id` 推导

**理由**：避免前端传错归属，确保 parse 生成的 normalized annotation 与源文件属于同一 session_video

### Decision 3: upsert + revision 而非完整 versioning

**选择**：同 `annotation_file_id` 多次 parse → upsert 同一条 normalized_annotation → `revision += 1`

**替代方案**：每次 parse 生成新记录，保留完整版本历史

**理由**：MVP 阶段简化实现；`revision` 字段保留未来扩展为完整版本历史的能力；`annotation_file_id` UNIQUE 约束保证一个文件只对应一条当前标准化结果

### Decision 4: `scale` 可空

**选择**：`scale` 在 DB 和 Pydantic 层面设为可空；缺少 scale 时 quality checker 标记 level 为 error/warning 并禁用距离相关模块

**理由**：MVP 阶段 Kinovea 导出常不含标尺信息；缺少 scale 仍可计算角度和阶段时长，只是不能计算速度和划幅

### Decision 5: `quality` JSONB 不做严格 Pydantic 校验

**选择**：仅约束 `quality.level` 为枚举（good/warning/error），其余字段用 dict/list 承接，Pydantic 设置 `extra="allow"`

**理由**：quality schema 会频繁迭代（新增检查项、模块、阈值），严格校验需要同步改 migration；service 层手动 `AnnotationQuality.model_validate(row.quality)` 处理 JSONB→Pydantic 转换

### Decision 6: 事件级 `labeled_by` 区分于顶层 `source`

**选择**：事件级标注来源使用 `labeled_by`（manual / kinovea / ai / derived），顶层使用 `source`（复用 `AnnotationSource` 枚举）

**理由**：两个 `source` 在不同层级语义不同，避免混淆

### Decision 7: `coordinate_system` 保留独立 JSONB 列

**选择**：独立存储，不合并到 `annotation_metadata`

**理由**：未来多机位（侧面/正面/俯视/水下）和 AI 归一化坐标的坐标系定义差异大，独立列便于 quality checker 读取和后续坐标变换处理

### Decision 8: `metadata` 在 SQLAlchemy 层映射为 `annotation_metadata`

**选择**：Python 属性 `annotation_metadata`，数据库列名 `metadata`

**理由**：SQLAlchemy Base 已占用 `metadata` 属性名（Change #1 已踩坑）

### Decision 9: `created_by` 与 `uploaded_by` 语义区分

**选择**：保留 `annotation_files.uploaded_by`（文件上传人）和 `normalized_annotations.created_by`（标注创建/解析触发人）的语义差异，不强行统一

**理由**：上传人和解析人可能是不同角色（教练上传文件，技术人员触发解析）

### Decision 10: `analysis_results` 引用字段留到后续 change

**选择**：本 change 不在 `analysis_results` 新增 `input_type` / `input_ref_id` 字段

**理由**：`analysis_results` 仍被 model_service mock 链路使用，贸然改字段可能破坏现有功能；在后续 metrics engine change 统一处理更安全

## Risks / Trade-offs

- **[Risk] `annotation_file_id` UNIQUE 约束**：PostgreSQL 中多个 NULL 视为不同值，manual JSON 创建的记录（annotation_file_id=NULL）可有多条。但若未来某场景需要同一文件生成多条 normalized annotation（如不同版本的 parser），UNIQUE 约束会成为障碍。→ **Mitigation**：此时改为普通索引 + service 层 upsert 查询。

- **[Risk] JSONB 嵌套字段无数据库层校验**：events、keypoint_frames 等字段的结构正确性完全依赖 service 层。若 parser 输出格式 bug，DB 会静默接受错误数据。→ **Mitigation**：quality checker 做结构性检查（required events 是否存在、关键点是否覆盖核心关节），parse endpoint 返回前做 schema 校验。

- **[Risk] `scale` 可空导致部分报告模块不可用**：教练上传标注后若缺少 scale，报告可能为空。→ **Mitigation**：quality checker 明确标记 disabled_modules，前端根据 quality.level 和 disabled_modules 提示用户补充标尺信息。

- **[Risk] 与 model_service mock 链路并跑期的混乱**：同一 session 可能同时有 `normalized_annotations`（来自 parse）和 `analysis_results`（来自 mock），报告读取哪份？→ **Mitigation**：本 change 不改 report builder，report 继续使用 `analysis_results`。后续 metrics engine change 切换读取来源。

## Migration Plan

1. 创建 Alembic 迁移文件（如 `20260706_0003_add_normalized_annotations.py`）
2. 创建 `normalized_annotations` 表，含 `session_video_id` 外键、`annotation_file_id` 可空外键 + UNIQUE 约束、JSONB 列、`revision` 字段
3. 部署执行 `alembic upgrade head`
4. 回滚：`alembic downgrade -1`
5. 不涉及数据迁移，新表初始为空
6. 不修改 `analysis_results` 表

## Open Questions

- Kinovea CSV parser 的具体实现推迟到 Change 2.5
- `analysis_results.input_type` / `input_ref_id` 字段留到 metrics engine change
