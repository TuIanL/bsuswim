## Why

当前系统有一条从 `training_session + session_videos → model_service → analysis_results → report_metadata` 的基础分析链路，但 `analysis_results` 同时承载了"空间-时间观测数据"（keypoint_frames、phases）和"计算分析输出"（metrics、diagnostics）两类职责。这导致后续接入 Kinovea 人工标注、Dartfish、AI 姿态识别或多机位融合时，每种新数据源都必须适配 `analysis_results` 的结构，而不是进入一个稳定的"标准标注层"。本 change 在已完成的 `annotation_files`（Change #1：原始标注文件持久化）和现有的 `analysis_results` 之间插入一个标准化观测层，将不同来源的标注数据统一为 `normalized_annotations`，使后续 metrics engine 和 diagnostics engine 不再依赖任何一种具体标注工具。

## What Changes

- 新增 `normalized_annotations` 数据库表，以 `session_video_id` 为单一外键关联 `session_videos`
- 使用 `annotation_file_id` 可空外键关联原始标注文件，支持从文件解析和直接 JSON 创建两种路径
- 定义 `swim-annotation.v1` JSON schema，统一 events、keypoint_frames、trajectories、manual_tags、scale、coordinate_system、quality 子结构
- 复用 Change #1 的 `AnnotationSource` 枚举
- 实现 annotation quality checker，根据 fps、events、keypoint_frames、scale 完整性生成 quality.level
- 提供创建、查询、列表标准化标注的 REST API
- 提供 `POST /api/annotations/{annotation_file_id}/parse` 骨架端点（Kinovea parser 留到 Change 2.5），parse 成功/失败联动更新 `annotation_files.status`
- 同 `annotation_file_id` 重复 parse 时 upsert 现有记录并递增 `revision`

## Capabilities

### New Capabilities
- `normalized-annotation-schema`: 定义标准化标注数据模型、JSON schema、quality checker、创建与查询 API，作为后续 metrics 和 diagnostics 的唯一观测输入格式

### Modified Capabilities
- `annotation-file-persistence`: parse endpoint 联动更新 `annotation_files.status`（uploaded → parsed / parse_failed）；复用 `AnnotationSource` 枚举
- `backend-platform-core`: 新增 `normalized_annotations` 表及对应 API 端点注册

## Impact

- 受影响代码：`backend/app/models`（新增 NormalizedAnnotation 模型）、`backend/app/schemas`（新增 Pydantic schema）、`backend/app/api/routes`（新增 normalized annotations 路由）、`backend/app/services`（新增 quality checker）、`backend/alembic`（新增迁移）
- `annotation_files.status` 字段将在 parse 成功/失败时被本 change 更新
- 不修改 `analysis_results` 表结构，但 design 中明确未来 metrics engine 应读取 `normalized_annotations` 而非 model_service mock
- 前端暂不要求改动，但后续工作台或报告页将依赖本 change 提供的标准化标注数据
