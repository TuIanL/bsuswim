# 数据库设计

## 1. 设计目标

当前数据库设计服务于 MVP 阶段的四个核心能力：

- 记录上传视频
- 记录分析任务状态
- 保存模型返回的结构化结果
- 保存报告生成结果

当前实现位于 [models.py](/Users/tuian/Documents/大学/竞赛/大创/游泳/swim/backend/app/models.py)。

## 2. 表结构总览

```text
video_files
    └── 1:N analysis_tasks
              └── 1:1 analysis_results
              └── 1:1 report_metadata
```

## 3. 表说明

### 3.1 `video_files`

上传视频主表。

主要字段：

- `id`: 主键
- `original_filename`: 用户原始文件名
- `stored_filename`: 本地落盘文件名
- `storage_path`: 存储路径，后期可演进为 object key
- `mime_type`: 文件 MIME type
- `size_bytes`: 文件大小
- `checksum_sha256`: 文件校验值
- `created_at`: 上传时间

设计意图：

- 将文件元数据和任务分离，允许一个视频被多次分析
- 为后期从本地文件迁移到对象存储保留字段语义空间

### 3.2 `analysis_tasks`

分析任务主表。

主要字段：

- `id`: 主键
- `video_id`: 关联 `video_files.id`
- `status`: 任务状态枚举
- `progress`: 0-100 进度值
- `stage`: 当前阶段标签
- `session_metadata`: 训练元数据 JSON
- `error_message`: 错误原因
- `created_at`: 创建时间
- `updated_at`: 更新时间
- `completed_at`: 完成时间

当前状态枚举：

- `uploaded`
- `queued`
- `processing`
- `result_saving`
- `completed`
- `failed`

设计意图：

- 任务状态必须入库，不能只存在内存里
- 支持前端刷新后恢复状态
- 为后期切换 Celery + Redis 保持状态契约稳定

### 3.3 `analysis_results`

模型结果表。

主要字段：

- `id`: 主键
- `task_id`: 关联 `analysis_tasks.id`
- `schema_version`: 结果版本
- `detections`: 检测框 JSON
- `keypoint_frames`: 关键点帧序列 JSON
- `phases`: 动作阶段 JSON
- `metrics`: 指标 JSON
- `diagnostics`: 诊断结果 JSON
- `raw_result`: 原始完整结果 JSON
- `created_at`: 创建时间

设计意图：

- 一次任务对应一份主结果，故 `task_id` 唯一
- 先用 JSON 承接高维度模型输出，降低前期频繁改表成本
- 用 `schema_version` 约束前后端兼容

### 3.4 `report_metadata`

报告数据表。

主要字段：

- `id`: 主键
- `task_id`: 关联 `analysis_tasks.id`
- `source`: 报告来源，当前默认 `model_service`
- `report_data`: 报告 JSON
- `generated_at`: 生成时间

设计意图：

- 将报告作为分析结果的下游派生物独立存储
- 为后期报告重生成、版本演化、PDF 导出留空间

## 4. 当前关系设计

- 一个视频可以创建多个分析任务
- 一个任务最多对应一份分析结果
- 一个任务最多对应一份报告数据

这是当前 MVP 最稳的结构。如果后面需要支持“同一任务多版本推理结果”或“多次报告生成”，可以把 1:1 调整为 1:N。

## 5. 当前不足与后续演进

### 5.1 缺少用户体系

当前没有：

- 用户表
- 教练/运动员表
- 项目或训练分组表

后续如接入登录与权限，需要新增业务主体表并把视频、任务挂到用户或项目下。

### 5.2 缺少数据库迁移工具

当前后端启动时直接 `create_all`。开发期方便，但正式环境建议引入：

- `Alembic`

### 5.3 JSON 字段较多

这是当前有意为之。原因是：

- 模型输出迭代快
- 指标字段还不稳定
- 先保证链路跑通

当某些指标和查询维度稳定后，可以把高频查询字段从 JSON 中抽出为结构化列。

## 6. 推荐索引方向

当前模型中已经包含主键和部分索引，后期建议补充：

- `analysis_tasks(status, updated_at)`
- `analysis_tasks(video_id)`
- `analysis_results(task_id)`
- `report_metadata(task_id)`

如果未来按用户或项目查询，再增加对应组合索引。
