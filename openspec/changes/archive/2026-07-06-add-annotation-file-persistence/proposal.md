## Why

当前项目已经具备训练记录、视频上传、分析任务和报告展示的基础骨架，但仍缺少对人工标注产物的系统化管理能力。近期基地试用将以“侧面视频拍摄 + Kinovea 人工标注 + 自动生成报告”的半自动流程为主，因此必须先让系统能够稳定保存原始标注文件、版本和归属关系，为后续解析、指标计算、规则诊断和报告生成建立可追溯输入。

## What Changes

- 新增标注文件持久化能力，支持将 Kinovea 等工具导出的原始标注文件上传并关联到训练记录和视频文件。
- 为标注文件保存来源、机位、文件类型、版本、上传人、文件校验信息和可选视频上下文元数据。
- 支持同一视频保留多版标注文件，不覆盖历史版本，并为后续解析流程预留状态字段。
- 提供按训练记录和视频查询标注文件列表与详情的后端 API。
- 为未来 `annotation parsing -> normalized annotation -> metrics / diagnostics -> report` 流水线提供稳定引用边界，但本 change 不实现解析、计算或报告生成。

## Capabilities

### New Capabilities
- `annotation-file-persistence`: 管理原始标注文件的上传、存储、版本化、归属关系和查询能力。

### Modified Capabilities
- `backend-platform-core`: 扩展业务后端核心能力，使训练记录和视频关系之上支持标注文件持久化 API 与数据模型。

## Impact

- 受影响代码主要位于 `backend/app/models`、`backend/app/schemas`、`backend/app/api/routes`、`backend/app/services` 和 `backend/alembic`。
- 需要新增标注文件持久化表、Pydantic schema、上传与查询 API，以及与现有 `training_sessions` / `video_files` 的归属校验逻辑。
- 可能需要复用现有本地 `uploads` 存储边界，并为未来迁移 MinIO 保持兼容。
- 前端主流程可暂不改动，但后续工作台或报告流水线将依赖本 change 提供的标注文件引用。
