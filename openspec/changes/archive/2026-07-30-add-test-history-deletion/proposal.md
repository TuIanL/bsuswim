## Why

测试任务一旦创建，会同时留下视频、标注、分析结果、报告和视觉资产。当前系统没有删除入口和受控的清理流程，用户无法移除过期或误建的历史记录，磁盘与数据库中的数据也会持续累积。

## What Changes

- 为教练拥有的测试任务提供不可恢复的删除能力，并在测试任务列表中提供明确的删除入口和二次确认。
- 新增按训练记录删除的受权 REST API，拒绝删除不存在或不属于当前教练的记录。
- 删除训练记录时级联清理其任务、分析结果、报告、AI 解读、会话视频、标注、标准化标注、指标、复核结论和运动学资产等数据库内容。
- 根据受控的数据库文件路径删除关联的原始视频、标注文件、运动学资产目录和报告 PDF；仅删除不再被任何会话引用的视频文件。
- 删除正在排队或执行的分析任务时返回明确的冲突结果，避免后台任务在删除期间继续写入。

## Capabilities

### New Capabilities
- `test-history-deletion`: 教练删除单条历史测试记录时，对关联数据库内容和上传文件进行安全、完整、不可恢复的清理。

### Modified Capabilities
- `vue-core-business-workflow`: 测试任务列表和运动员档案历史记录提供删除操作、确认反馈和删除后的列表同步。

## Impact

- 前端：`frontend-vue/src/views/TasksView.vue`、运动员档案历史列表、API 客户端和 demo 数据。
- 后端：训练记录路由、删除编排服务、SQLAlchemy 模型关系、数据库迁移及 API 测试。
- 存储：`backend/uploads` 下的原始上传文件、`kinematic-artifacts` 和 `reports` 衍生目录。
- API：新增 `DELETE /api/v1/sessions/{session_id}`，成功后不保留可读取的关联记录或文件。
