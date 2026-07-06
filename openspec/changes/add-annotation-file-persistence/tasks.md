## 1. Database Migration

- [x] 1.1 创建 Alembic 迁移文件，新增 `annotationsource` 和 `annotationfilestatus` PostgreSQL ENUM 类型
- [x] 1.2 创建 `annotation_files` 表，包含 `session_video_id` 外键（引用 `session_videos.id`，ON DELETE CASCADE）、`source` ENUM、`status` ENUM、文件元信息字段、`annotation_fps`、`version`、`metadata` JSONB、时间戳字段
- [x] 1.3 添加唯一约束 `uq_annotation_file_session_video_source_version`（`session_video_id, source, version`）
- [x] 1.4 添加常用索引：`ix_annotation_files_session_video`、`ix_annotation_files_status`、`ix_annotation_files_source`
- [x] 1.5 验证 migration 可正常执行 `alembic upgrade head` 和回滚 `alembic downgrade -1`

## 2. ORM Model

- [x] 2.1 在 `backend/app/models/` 下新建 `annotation.py`，定义 `AnnotationSource` 和 `AnnotationFileStatus` Python Enum
- [x] 2.2 定义 `AnnotationFile` ORM 模型（SQLAlchemy 2.0 Mapped 风格），包含 `session_video` relationship
- [x] 2.3 在 `SessionVideo` 模型中新增 `annotations` back-reference relationship
- [x] 2.4 在 `backend/app/models/__init__.py` 中导出新模型和枚举

## 3. Pydantic Schemas

- [x] 3.1 在 `backend/app/schemas/` 下新建 `annotation.py`，定义 `AnnotationFileCreate`（上传请求 schema）
- [x] 3.2 定义 `AnnotationFileRead`（列表项和详情响应 schema），包含通过 relationship 获取的 `session_id`、`video_file_id`、`view_type`
- [x] 3.3 定义 `AnnotationFileArchiveResponse`（归档响应 schema）
- [x] 3.4 在 `backend/app/schemas/__init__.py` 中导出新 schema

## 4. Storage & Checksum

- [x] 4.1 确认现有 `StorageService.save_upload()` 可接受非视频文件（csv/json/xml/txt），必要时调整 mime_type 校验
- [x] 4.2 实现 `detect_file_type()` 工具函数，根据文件扩展名推断 `file_type`（csv/json/xml/txt/kva/unknown）
- [x] 4.3 实现 `validate_annotation_file()` 校验函数：检查文件非空、类型在允许列表中、大小不超过上限

## 5. Repository Layer

- [x] 5.1 在 `backend/app/repositories/` 下新建 `annotation_repository.py`
- [x] 5.2 实现 `get_max_version(db, session_video_id, source) → int` 查询当前最大版本号
- [x] 5.3 实现 `list_by_session_video(db, session_video_id) → list[AnnotationFile]` 查询标注文件列表
- [x] 5.4 实现 `get_with_ownership_check(db, annotation_file_id, current_user_id) → AnnotationFile` 带权限校验的详情查询

## 6. Service Layer

- [x] 6.1 在 `backend/app/services/` 下新建 `annotation_file_service.py`
- [x] 6.2 实现 `create_annotation()` 方法：接收 file、session_video_id、source、annotation_fps、metadata、uploaded_by → 调用 StorageService 保存 → 计算 version → 创建 DB 记录 → 返回 AnnotationFile
- [x] 6.3 实现 `archive_annotation()` 方法：校验权限 → 更新 status 为 `archived`

## 7. API Routes

- [x] 7.1 在 `backend/app/api/routes/` 下新建 `annotations.py`
- [x] 7.2 实现 `POST /api/v1/sessions/{session_id}/videos/{video_id}/annotations` 上传端点：权限校验 → 查找 `session_video_id` → 校验文件 → 调用 service → 返回 201
- [x] 7.3 实现 `GET /api/v1/sessions/{session_id}/videos/{video_id}/annotations` 列表端点：权限校验 → 查找 `session_video_id` → 查询标注列表 → 返回
- [x] 7.4 实现 `GET /api/v1/annotations/{annotation_file_id}` 详情端点：权限校验链路 → 返回 AnnotationFileRead
- [x] 7.5 实现 `GET /api/v1/annotations/{annotation_file_id}/download` 下载端点：权限校验 → FileResponse 返回原始文件
- [x] 7.6 实现 `POST /api/v1/annotations/{annotation_file_id}/archive` 归档端点：权限校验 → 更新 status → 返回
- [x] 7.7 定义清晰的错误响应：`VIDEO_NOT_IN_SESSION`、`UNSUPPORTED_ANNOTATION_FILE_TYPE`、`EMPTY_ANNOTATION_FILE`

## 8. Router Registration

- [x] 8.1 在 `backend/app/api/router.py` 中注册 `annotations` router（prefix="/annotations"，tags=["annotations"]）
- [x] 8.2 在上传和列表端点中复用 `sessions` router 的 `_get_owned_session` 或将其提升为共享依赖

## 9. Frontend Minimal Entry

- [x] 9.1 在训练记录详情页或视频详情页新增"标注文件"区域，包含上传按钮（选择文件 + source 下拉 + 可选 annotation_fps 输入）
- [x] 9.2 上传成功后显示标注文件信息卡片：文件名、来源、机位、版本、状态、上传时间
- [x] 9.3 展示当前视频的标注文件列表（含版本历史和状态标签）

## 10. Tests

- [x] 10.1 编写 API 集成测试：上传标注文件成功场景（201）
- [x] 10.2 编写 API 集成测试：查询标注文件列表和详情
- [x] 10.3 编写 API 集成测试：版本号自动递增验证
- [x] 10.4 编写 API 集成测试：归档标注文件
- [x] 10.5 编写 API 集成测试：错误场景（session 不存在、视频未绑定、不支持的文件类型、空文件）
- [x] 10.6 编写 API 集成测试：跨 session 版本隔离验证
- [x] 10.7 编写 API 集成测试：下载标注文件
