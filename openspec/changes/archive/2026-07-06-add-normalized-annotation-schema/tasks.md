## 1. Database Migration

- [x] 1.1 创建 Alembic 迁移文件 `20260706_0003_add_normalized_annotations.py`，新增 `normalized_annotations` 表
- [x] 1.2 添加 `session_video_id` 外键（引用 `session_videos.id`，ON DELETE CASCADE）
- [x] 1.3 添加 `annotation_file_id` 可空外键（引用 `annotation_files.id`）+ UNIQUE 约束
- [x] 1.4 添加 `revision` 字段（INTEGER NOT NULL DEFAULT 1）
- [x] 1.5 添加 JSONB 列：`scale`、`coordinate_system`、`events`、`keypoint_frames`、`trajectories`、`manual_tags`、`quality`、`metadata`
- [x] 1.6 添加常用索引：`session_video_id`、`annotation_file_id`
- [x] 1.7 验证 migration 可正常执行和回滚

## 2. ORM Model

- [x] 2.1 在 `backend/app/models/` 下新建 `normalized_annotation.py`，定义 `NormalizedAnnotation` ORM 模型（SQLAlchemy 2.0 Mapped 风格）
- [x] 2.2 Python 属性 `annotation_metadata` 映射到数据库列 `metadata`（避免与 SQLAlchemy Base.metadata 冲突）
- [x] 2.3 添加 `session_video` relationship 和 `annotation_file` relationship
- [x] 2.4 在 `SessionVideo` 模型中新增 `normalized_annotations` back-reference relationship
- [x] 2.5 在 `backend/app/models/__init__.py` 中导出新模型

## 3. Pydantic Schemas

- [x] 3.1 在 `backend/app/schemas/` 下新建 `normalized_annotation.py`，定义 `AnnotationQuality` Pydantic 模型（`level` 枚举 + `extra="allow"`）
- [x] 3.2 定义子结构 Pydantic 模型：`AnnotationEvent`（含 `labeled_by`）、`KeypointFrame`、`Trajectory`、`ManualTag`、`ScaleInfo`、`CoordinateSystem`
- [x] 3.3 定义 `NormalizedAnnotationCreate`（创建请求 schema，包含可选的 `annotation_file_id`）
- [x] 3.4 定义 `NormalizedAnnotationRead`（响应 schema，包含完整 JSON + 通过 relationship 获取的 `session_id`、`video_file_id`、`view_type`）
- [x] 3.5 定义 `NormalizedAnnotationListItem`（列表摘要 schema）和 `ParseResponse`（parse 响应 schema）
- [x] 3.6 在 `backend/app/schemas/__init__.py` 中导出新 schema

## 4. Quality Checker

- [x] 4.1 在 `backend/app/services/` 下新建 `quality_checker.py`
- [x] 4.2 实现 `check_has_fps(fps)` 检查
- [x] 4.3 实现 `check_has_events(events)` 检查
- [x] 4.4 实现 `check_has_keypoint_frames(keypoint_frames)` 检查
- [x] 4.5 实现 `check_has_core_keypoints(keypoint_frames)` 检查（至少含肩/肘/腕/髋/膝/踝）
- [x] 4.6 实现 `check_has_scale(scale)` 检查（含 `pixels_per_meter`）
- [x] 4.7 实现 `check_event_frame_range(events, frame_count)` 检查
- [x] 4.8 实现 `check_keypoint_frame_range(keypoint_frames, frame_count)` 检查
- [x] 4.9 实现 `evaluate_quality(data) → AnnotationQuality` 聚合函数，根据检查结果决定 level（good/warning/error）和 modules

## 5. Repository Layer

- [x] 5.1 在 `backend/app/repositories/` 下新建 `normalized_annotation_repository.py`
- [x] 5.2 实现 `get_by_annotation_file(db, annotation_file_id) → NormalizedAnnotation | None` 查询（用于 upsert 判断）
- [x] 5.3 实现 `list_by_session_video(db, session_video_id) → list[NormalizedAnnotation]`
- [x] 5.4 实现 `get_with_ownership_check(db, normalized_annotation_id, current_user_id) → NormalizedAnnotation` 带权限校验的详情查询

## 6. Service Layer

- [x] 6.1 在 `backend/app/services/` 下新建 `normalized_annotation_service.py`
- [x] 6.2 实现 `create_normalized_annotation()` 方法：接收 session_video_id、annotation_file_id（可选）、schema 数据 → 运行 quality checker → 创建 DB 记录 → 返回
- [x] 6.3 实现 `parse_annotation_file()` 方法：接收 annotation_file_id → 推导 session_video_id → 执行解析（MVP 返回 501 或对 manual_json 读取） → 调用 quality checker → upsert 记录（revision 递增） → 联动更新 annotation_files.status
- [x] 6.4 实现 `update_annotation_file_status()` 辅助方法：parse 成功设 `parsed`，失败设 `parse_failed` + `parse_error`

## 7. API Routes

- [x] 7.1 在 `backend/app/api/routes/` 下新建 `normalized_annotations.py`
- [x] 7.2 实现 `POST /api/v1/session-videos/{session_video_id}/normalized-annotations` 创建端点
- [x] 7.3 实现 `GET /api/v1/normalized-annotations/{normalized_annotation_id}` 详情端点（含权限校验链路）
- [x] 7.4 实现 `GET /api/v1/session-videos/{session_video_id}/normalized-annotations` 列表端点
- [x] 7.5 实现 `POST /api/v1/annotations/{annotation_file_id}/parse` 解析骨架端点
- [x] 7.6 定义清晰的错误响应：`ANNOTATION_FILE_NOT_FOUND`、`PARSE_NOT_IMPLEMENTED`、`QUALITY_ERROR`

## 8. Router Registration

- [x] 8.1 在 `backend/app/api/router.py` 中注册 `normalized_annotations` router（不带 prefix，路由路径自带前缀）
- [x] 8.2 确认权限校验链路：`normalized_annotation → session_video → training_session → coach`

## 9. Sample Data & Documentation

- [x] 9.1 创建 `backend/samples/side-view-freestyle-v1.json` 示例文件（完整 MVP NormalizedAnnotation JSON）
- [x] 9.2 在 `docs/ai-api-spec.md` 中补充 NormalizedAnnotation 作为分析链路输入层的说明

## 10. Tests

- [x] 10.1 编写 quality checker 单元测试：完整数据 → good
- [x] 10.2 编写 quality checker 单元测试：缺 scale → warning
- [x] 10.3 编写 quality checker 单元测试：缺 keypoint_frames → error
- [x] 10.4 编写 API 集成测试：JSON 创建 normalized annotation 成功
- [x] 10.5 编写 API 集成测试：查询详情和列表
- [x] 10.6 编写 API 集成测试：parse endpoint 骨架
- [x] 10.7 编写 API 集成测试：parse 成功联动 annotation_files.status = parsed
- [x] 10.8 编写 API 集成测试：同 annotation_file_id 重复 parse → upsert + revision 递增
- [x] 10.9 编写 API 集成测试：跨 session_video 版本隔离
