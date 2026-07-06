## Context

当前项目已有完整的训练记录（`training_sessions`）、视频文件（`video_files`）、视频绑定（`session_videos`）、分析任务（`analysis_tasks`）、分析结果（`analysis_results`）和报告（`report_metadata`）数据模型及 API。但缺少对人工标注产物（Kinovea 等工具导出的原始标注文件）的系统化管理能力。

本设计为后续标注解析、指标计算、规则诊断和报告生成流水线提供"标注输入可管理、可追溯、可复用"的基础。标注文件不直接挂在 `video_files` 上，而是挂在 `session_videos` 上——因为标注是"某次训练分析任务中对某个机位视频进行的一次标注"，而非裸视频文件的属性。

现有技术栈：FastAPI + SQLAlchemy 2.0（Mapped 风格）+ PostgreSQL + Alembic + 本地文件存储。

## Goals / Non-Goals

**Goals:**

- 新增 `annotation_files` 表，以 `session_video_id` 为单一外键关联到 `session_videos`
- 支持上传、查询、详情、下载、归档原始标注文件的 REST API
- 同一 `session_video_id + source` 下版本号自动递增，保留历史版本
- 复用现有 `StorageService.save_upload()` 做文件保存和 SHA256 校验
- 为后续解析模块提供稳定的 `annotation_file_id` 引用

**Non-Goals:**

- 不解析 Kinovea 文件内容，不计算任何指标
- 不生成 `NormalizedAnnotation` 或分析结果
- 不实现 AI 自动姿态识别
- 不新增独立存储服务（MVP 复用现有 StorageService）

## Decisions

### Decision 1: 以 `session_video_id` 作为主关联

**选择**：`annotation_files.session_video_id → session_videos.id`（单一外键）

**替代方案**：`annotation_files.session_id + annotation_files.video_file_id + annotation_files.camera_view`（三字段方案）

**理由**：
- `session_videos` 已经是"某次训练中的某个视频素材及其机位属性"的标准表达，标注的业务语义与之完全一致
- 避免 `camera_view` 与 `session_videos.view_type` 重复存储和潜在不一致
- 不同 session 复用同一个 `video_file_id` 时，标注版本不会串号
- 查询链路清晰：`annotation → session_video → session + video`

### Decision 2: 版本号作用域为 `session_video_id + source`

**选择**：同一 `session_video_id + source` 下自动递增版本号

**替代方案**：按 `video_file_id + source + camera_view` 作用域

**理由**：
- `camera_view` 已由 `session_videos.view_type` 表达，无需重复参与版本计算
- 版本在 session 维度下独立递增，同一视频在不同 session 中的标注版本各自从 1 开始

### Decision 3: `annotation_fps` 独立于 `session_videos.fps`

**选择**：保留两个 fps 字段，语义区分
- `session_videos.fps`：视频实际录制帧率
- `annotation_files.annotation_fps`：标注文件使用的时间基准

**理由**：
- Kinovea 等工具导出时可能使用与视频不同的时间基准（如视频 60fps，标注导出 30fps）
- 后续解析模块需要 `annotation_fps` 来做帧号→时间戳的正确换算
- 命名为 `annotation_fps` 避免与视频 fps 混淆

### Decision 4: MVP 复用现有 StorageService

**选择**：直接调用 `StorageService.save_upload()` 处理标注文件

**替代方案**：新建 `AnnotationStorageService`，使用语义化路径

**理由**：
- `save_upload()` 已提供文件保存、UUID 重命名、SHA256 校验的成熟逻辑
- 本 change 目标是"标注文件持久化"，不是重构存储基础设施
- 物理路径虽不表达 session/video/version，但数据库记录已提供完整追溯
- 后续资产（标注文件、证据图、报告）增多后再统一升级存储层

### Decision 5: source 和 status 使用 Python Enum + PostgreSQL ENUM

**选择**：遵循现有 `ViewType`、`AnalysisTaskStatus` 模式

```python
class AnnotationSource(str, PyEnum):
    KINOVEA = "kinovea"
    DARTFISH = "dartfish"
    MANUAL_JSON = "manual_json"
    AI_POSE = "ai_pose"
    UNKNOWN = "unknown"

class AnnotationFileStatus(str, PyEnum):
    UPLOADED = "uploaded"
    PARSED = "parsed"
    PARSE_FAILED = "parse_failed"
    ARCHIVED = "archived"
```

**理由**：与现有代码风格一致，数据库层面有类型约束

### Decision 6: 归档代替物理删除

**选择**：`POST /api/annotations/{id}/archive` 仅更新 status 为 `archived`

**理由**：
- 历史报告可继续追溯到旧标注文件
- 避免因误删导致报告来源断裂
- 符合"可追溯数据资产"的定位

### Decision 7: API 路由结构

**选择**：上传和列表使用 session 嵌套 URL，详情/下载/归档使用顶层 annotation URL

| 操作 | 方法 | URL |
|------|------|-----|
| 上传 | POST | `/api/sessions/{session_id}/videos/{video_id}/annotations` |
| 列表 | GET | `/api/sessions/{session_id}/videos/{video_id}/annotations` |
| 详情 | GET | `/api/annotations/{annotation_file_id}` |
| 下载 | GET | `/api/annotations/{annotation_file_id}/download` |
| 归档 | POST | `/api/annotations/{annotation_file_id}/archive` |

**理由**：
- 上传/列表与现有 `POST/GET /sessions/{id}/videos` 模式一致
- 详情/下载/归档用顶层路径避免过深的 URL 嵌套
- 所有端点都通过 `_get_owned_session` 或 annotation → session_video → session 链路做权限校验

## Risks / Trade-offs

- **[Risk] session_videos.id 为 Integer 类型**：若未来 session_videos 数据量极大（>21 亿），需迁移为 BigInteger。当前项目规模下 Integer 足够。→ **Mitigation**：使用 `Integer` 对齐现有类型，后续如有需要统一迁移。

- **[Risk] 复用 StorageService 导致标注文件和视频文件混在同一 uploads/ 目录**：通过 `stored_filename`（UUID）可区分文件，数据库记录提供完整归属。→ **Mitigation**：存储层升级时按 `file_type` 或表名迁移到子目录。

- **[Risk] 没有阻止重复文件上传**：同一份标注文件多次上传会创建多条记录。→ **Mitigation**：MVP 仅保存 `checksum_sha256` 不做去重拦截，后续可在上传前查询 checksum 是否存在来提示用户。

- **[Risk] `uploaded_by` 为可空字段**：若未登录或 token 过期仍可上传（取决于路由是否挂 `Depends(get_current_user)`）。→ **Mitigation**：所有 annotation 端点统一挂 `Depends(get_current_user)`，`uploaded_by` 从 token 提取，NOT NULL。

## Migration Plan

1. 创建 Alembic 迁移文件（如 `20260706_0002_add_annotation_files.py`）
2. 创建 PostgreSQL ENUM 类型：`annotationsource`、`annotationfilestatus`
3. 创建 `annotation_files` 表，含外键、唯一约束和索引
4. 部署时执行 `alembic upgrade head`
5. 回滚：`alembic downgrade -1` 删除表及 ENUM 类型
6. 本 change 不涉及数据迁移，新表初始为空

## Open Questions

- 无。核心设计决策已在 explore 阶段充分讨论并收敛。
