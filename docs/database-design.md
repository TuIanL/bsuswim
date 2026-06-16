# 数据库设计

## 1. 设计目标

当前数据库设计已经从“单视频分析 Demo”升级为“训练记录为中心的平台后端骨架”，核心目标是：

- 管理教练用户和登录认证
- 管理运动员档案
- 管理一次训练或测试记录
- 将多个视频文件按机位绑定到同一次训练记录
- 持久化 session 级 AI 分析任务、模型结果和报告数据

当前模型位于 [models/](/Users/tuian/Documents/大学/竞赛/大创/游泳/swim/backend/app/models)。

## 2. 表结构总览

```text
users
  └── athletes
        └── training_sessions
              ├── session_videos
              │     └── video_files
              ├── analysis_tasks
              │     └── analysis_results
              └── report_metadata

teams
  └── athletes
```

## 3. 核心表说明

### 3.1 `users`

保存平台登录用户。第一版主要服务教练账号。

关键字段：

- `username`
- `email`
- `phone`
- `password_hash`
- `role`
- `is_active`

### 3.2 `athletes`

保存运动员档案，并通过 `coach_id` 关联当前教练。

关键字段：

- `name`
- `gender`
- `birth_date`
- `height_cm`
- `weight_kg`
- `stroke_specialty`
- `level`
- `coach_id`
- `team_id`

### 3.3 `training_sessions`

一次训练或测试记录，是平台分析链路的业务中心。

关键字段：

- `athlete_id`
- `coach_id`
- `title`
- `session_date`
- `venue`
- `stroke_type`
- `distance_m`
- `pool_length_m`
- `status`

### 3.4 `video_files`

只记录文件存储事实，不直接承载训练业务含义。

关键字段：

- `original_filename`
- `stored_filename`
- `storage_path`
- `mime_type`
- `size_bytes`
- `checksum_sha256`

### 3.5 `session_videos`

记录视频文件在某次训练记录中的业务角色。

关键字段：

- `session_id`
- `video_file_id`
- `view_type`
- `fps`
- `resolution`
- `sync_offset_ms`

这个表让一个训练记录可以绑定侧面、正面、水下等多机位视频。

### 3.6 `analysis_tasks`

保存 session 级分析任务状态。

关键字段：

- `session_id`
- `status`
- `progress`
- `stage`
- `request_payload`
- `error_message`
- `completed_at`

### 3.7 `analysis_results`

保存模型服务返回的结构化结果。

关键字段：

- `task_id`
- `schema_version`
- `detections`
- `keypoint_frames`
- `phases`
- `metrics`
- `diagnostics`
- `raw_result`

### 3.8 `report_metadata`

保存训练记录报告 JSON。

关键字段：

- `session_id`
- `task_id`
- `source`
- `report_data`
- `generated_at`

## 4. Migration

业务数据库使用 PostgreSQL，schema 由 Alembic 管理：

```bash
cd backend
alembic upgrade head
```

后续修改模型后，应生成新的 migration 并检查差异：

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

## 5. 设计边界

- `video_files` 是文件层，`session_videos` 是业务关系层。
- `analysis_tasks` 绑定 `session_id`，而不是单个 `video_id`。
- 模型输出先用 JSON 字段承接，等指标稳定后再抽结构化列。
- 文件存储第一版使用本地 `uploads/`，后续可迁移到 MinIO。
