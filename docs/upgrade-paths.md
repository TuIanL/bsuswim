# 后期升级边界

## 本地 uploads 到 MinIO

当前业务代码通过 `StorageService` 保存上传视频，并在数据库中记录 `storage_path` 与 `stored_filename`。迁移到 MinIO 时，优先替换以下边界：

- `backend/app/services/storage.py`
- `VideoFile.storage_path` 字段语义从本地路径调整为 object key 或对象 URL
- 静态 `/uploads` 挂载替换为签名 URL 或后端代理下载 API

API 调用方不应依赖本地绝对路径，只使用后端返回的 `playback_url` 或后续对象引用。

## BackgroundTasks 到 Celery + Redis

当前业务代码通过 `BackgroundTasks` 调用 `run_analysis_task(task_id)`。迁移到 Celery + Redis 时，保持以下契约不变：

- `POST /api/v1/analysis/submit` 仍基于 `session_id` 返回任务 ID 和初始状态
- `GET /api/v1/analysis/{task_id}/status` 仍读取数据库任务状态
- `GET /api/v1/analysis/{task_id}/result` 仍读取已保存分析结果
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

## 进程内 AI 解读调度到持久队列

AI 报告解读当前通过独立的 `InterpretationScheduler` 协议和进程内线程池执行。
数据库先保存 `pending` 状态，应用启动时会恢复 pending 或超时的 generating 任务。
迁移到 Celery/RQ/Redis worker 时保持以下边界：

- API 和 pipeline 只调用 `schedule(interpretation_id)`，不传递报告正文或凭据。
- worker 通过 ID 重新读取受控事实包并执行 `execute_interpretation`。
- 保留同一 report、generation signature、attempt 的幂等约束。
- 队列确认必须发生在 pending 记录提交之后；失败不得修改基础报告状态。
- 多实例部署必须替换当前进程内线程池，否则任务只在接收请求的实例上执行。
