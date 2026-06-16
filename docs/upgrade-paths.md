# 后期升级边界

## 本地 uploads 到 MinIO

当前业务代码通过 `StorageService` 保存上传视频，并在数据库中记录 `storage_path` 与 `stored_filename`。迁移到 MinIO 时，优先替换以下边界：

- `backend/app/services/storage.py`
- `VideoFile.storage_path` 字段语义从本地路径调整为 object key 或对象 URL
- 静态 `/uploads` 挂载替换为签名 URL 或后端代理下载 API

API 调用方不应依赖本地绝对路径，只使用后端返回的 `playback_url` 或后续对象引用。

## BackgroundTasks 到 Celery + Redis

当前业务代码通过 `BackgroundTasks` 调用 `run_analysis_task(task_id)`。迁移到 Celery + Redis 时，保持以下契约不变：

- `POST /api/v1/tasks` 仍返回任务 ID 和初始状态
- `GET /api/v1/tasks` 与 `GET /api/v1/tasks/{id}` 仍读取数据库任务状态
- 状态字段仍覆盖 `uploaded`、`queued`、`processing`、`result_saving`、`completed`、`failed`
- 前端轮询和报告读取方式不变

优先替换的执行边界：

- 将 `background_tasks.add_task(run_analysis_task, task.id)` 改为 Celery task enqueue
- 将 `run_analysis_task` 保持为可复用的任务处理函数或拆成 Celery task body
- 增加队列重试、超时、并发和监控配置

## Stub 模型服务到 YOLO/MMPose

当前 `model_service/app/runtime.py` 返回固定结构化结果。接入真实模型时保持 API 响应 schema：

- `schema_version`
- `detections`
- `keypoint_frames`
- `phases`
- `metrics`
- `diagnostics`
- `error_message`

模型服务可以单独安装 CUDA、PyTorch、OpenCV、MMPose、YOLO 权重和视频处理依赖，不应把这些重依赖加入业务后端。
