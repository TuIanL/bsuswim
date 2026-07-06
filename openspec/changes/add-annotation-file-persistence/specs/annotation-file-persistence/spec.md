# annotation-file-persistence Specification

## Purpose
管理原始标注文件的上传、存储、版本化、归属关系和查询能力。为后续标注解析、指标计算、规则诊断和报告生成流水线提供稳定输入引用。

## ADDED Requirements

### Requirement: Annotation file upload
系统 SHALL 支持为某个训练记录下已绑定的视频上传原始标注文件。

#### Scenario: Upload annotation file to session video
- **WHEN** 已登录调用方向 `POST /api/v1/sessions/{session_id}/videos/{video_id}/annotations` 提交有效的标注文件及 `source` 参数
- **THEN** 系统 MUST 通过 `session_videos` 找到对应的 `session_video_id`，保存文件，计算 SHA256 校验值，创建 `annotation_files` 记录，并返回标注文件元信息

#### Scenario: Upload to non-existent session
- **WHEN** 已登录调用方向不存在的 `session_id` 上传标注文件
- **THEN** 系统 MUST 返回 404 错误，提示训练记录不存在

#### Scenario: Upload to unbound video
- **WHEN** 已登录调用方向未绑定到该 session 的 `video_id` 上传标注文件
- **THEN** 系统 MUST 返回 404 错误，提示该视频未绑定到当前训练记录

#### Scenario: Upload unsupported file type
- **WHEN** 已登录调用方上传非 csv、json、xml、txt、kva 格式的标注文件
- **THEN** 系统 MUST 返回 400 错误，错误码为 `UNSUPPORTED_ANNOTATION_FILE_TYPE`

#### Scenario: Upload empty file
- **WHEN** 已登录调用方上传空文件
- **THEN** 系统 MUST 返回 400 错误，错误码为 `EMPTY_ANNOTATION_FILE`

### Requirement: Annotation file versioning
系统 SHALL 在同一 `session_video_id + source` 下自动递增版本号。

#### Scenario: First upload gets version 1
- **WHEN** 用户首次对某个 session video 上传 `source=kinovea` 的标注文件
- **THEN** 系统 MUST 分配 `version = 1`

#### Scenario: Subsequent upload increments version
- **WHEN** 用户再次对同一 session video 上传 `source=kinovea` 的标注文件
- **THEN** 系统 MUST 分配 `version = 2`

#### Scenario: Different source has independent version
- **WHEN** 用户对同一 session video 上传 `source=dartfish` 的标注文件
- **THEN** 系统 MUST 为该 source 独立从 `version = 1` 开始计数

#### Scenario: Cross-session version isolation
- **WHEN** 同一 `video_file_id` 绑定到两个不同 session 后分别上传标注文件
- **THEN** 系统 MUST 为每个 session 的标注版本独立计数，互不影响

### Requirement: Annotation file list query
系统 SHALL 支持查询某个 session video 下的全部标注文件。

#### Scenario: List annotations for a session video
- **WHEN** 已登录调用方请求 `GET /api/v1/sessions/{session_id}/videos/{video_id}/annotations`
- **THEN** 系统 MUST 返回该 session video 下所有标注文件的列表，包含 id、source、view_type、file_type、version、status、original_filename、annotation_fps、uploaded_at

#### Scenario: List annotations for session with no annotations
- **WHEN** 已登录调用方请求未上传过标注文件的 session video
- **THEN** 系统 MUST 返回空列表

### Requirement: Annotation file detail query
系统 SHALL 支持查看单个标注文件的完整详情，并通过标注文件 → session_video → training_session 链路做权限校验。

#### Scenario: Get annotation file detail
- **WHEN** 已登录调用方请求 `GET /api/v1/annotations/{annotation_file_id}`
- **THEN** 系统 MUST 返回该标注文件的完整元信息，包括 id、session_video_id、session_id、video_file_id、view_type、source、version、status、original_filename、stored_filename、storage_path、file_type、file_size_bytes、checksum_sha256、annotation_fps、metadata、uploaded_at

#### Scenario: Unauthorized annotation access
- **WHEN** 调用方请求不属于当前用户可访问训练记录的标注文件
- **THEN** 系统 MUST 返回 404 错误，不得泄露其他用户的标注文件数据

### Requirement: Annotation file download
系统 SHALL 支持下载原始标注文件内容。

#### Scenario: Download annotation file
- **WHEN** 已登录调用方请求 `GET /api/v1/annotations/{annotation_file_id}/download`
- **THEN** 系统 MUST 返回该标注文件的原始二进制内容，Content-Type 根据文件类型设置

#### Scenario: Download non-existent file
- **WHEN** 标注记录存在但物理文件已丢失
- **THEN** 系统 MUST 返回 404 错误，提示文件不存在

### Requirement: Annotation file archival
系统 SHALL 支持归档标注文件，不做物理删除。

#### Scenario: Archive annotation file
- **WHEN** 已登录调用方请求 `POST /api/v1/annotations/{annotation_file_id}/archive`
- **THEN** 系统 MUST 将该标注文件的 status 更新为 `archived`，并返回更新后的记录

#### Scenario: Archive already archived file
- **WHEN** 已登录调用方请求归档一个已处于 `archived` 状态的标注文件
- **THEN** 系统 MUST 返回成功，status 保持 `archived` 不变

### Requirement: Annotation file data model
系统 SHALL 以 `session_video_id` 为单一外键关联 `session_videos`，不冗余存储 `session_id`、`video_file_id`、`camera_view`。

#### Scenario: Annotation file references session video
- **WHEN** 创建标注文件记录
- **THEN** 系统 MUST 仅通过 `session_video_id` 外键关联到 `session_videos` 表

#### Scenario: Camera view inherited from session video
- **WHEN** 查询标注文件详情
- **THEN** 系统 MUST 通过 `session_videos.view_type` 返回机位信息，`annotation_files` 表本身不存储 `camera_view` 字段

### Requirement: Annotation FPS independent from video FPS
系统 SHALL 以 `annotation_fps` 字段存储标注文件使用的时间基准，与 `session_videos.fps` 语义区分。

#### Scenario: Annotation FPS differs from video FPS
- **WHEN** 用户上传标注文件时提供了 `annotation_fps` 参数
- **THEN** 系统 MUST 将 `annotation_fps` 保存到 `annotation_files` 记录，不与 `session_videos.fps` 混淆

#### Scenario: Annotation FPS is optional
- **WHEN** 用户上传标注文件时未提供 `annotation_fps`
- **THEN** 系统 MUST 允许该字段为空，后续解析模块可自行推断

### Requirement: Annotation file metadata
系统 SHALL 支持在上传时附加扩展元数据。

#### Scenario: Upload with metadata
- **WHEN** 用户上传标注文件时附带 `metadata` JSON 字段（如 `labeler_name`、`note`）
- **THEN** 系统 MUST 将 metadata 保存到 `annotation_files.metadata` JSONB 字段

### Requirement: Source and status enum constraints
系统 SHALL 约束 `source` 和 `status` 字段为预定义枚举值。

#### Scenario: Valid source values
- **WHEN** 创建或更新标注文件记录
- **THEN** 系统 MUST 仅接受 `kinovea`、`dartfish`、`manual_json`、`ai_pose`、`unknown` 作为 `source` 值

#### Scenario: Valid status values
- **WHEN** 创建标注文件记录
- **THEN** 系统 MUST 默认 status 为 `uploaded`，后续可流转为 `parsed`、`parse_failed`、`archived`
