## ADDED Requirements

### Requirement: Six-step guided side-view 2D kinematics workflow
系统 SHALL 在 `/sessions/:sessionId/upload` 提供可恢复的六步侧面二维运动学 Web 工作流：上传并绑定侧面视频、上传 CVAT Skeleton XML、自动解析并展示标注质量、确认四类运动学模块可用状态、提交并跟踪 annotation_kinematics 分析任务、查看 HTML 报告或导出/下载 PDF。

#### Scenario: User enters an upload page with no assets
- **WHEN** 用户进入一次训练记录的上传页且不存在任何侧面视频与标注
- **THEN** 系统 MUST 将当前工作流阶段推导为 `video_required`
- **AND** 仅展示侧面视频输入，不展示后续步骤的可操作内容

#### Scenario: Full guided loop completes
- **WHEN** 用户上传侧面视频、上传 CVAT XML、确认模块可用性并提交分析
- **THEN** 系统 MUST 在页面内持续展示真实流水线进度直至报告生成
- **AND** 报告完成后提供 HTML 报告入口与 PDF 导出/下载入口

### Requirement: Workflow phase derived from server state
系统 SHALL 根据服务端持久化状态推导当前工作流阶段，不依赖前端内存或 localStorage。

#### Scenario: Page reload during running task
- **WHEN** 用户刷新页面且最新 annotation_kinematics 任务处于 queued/processing
- **THEN** 系统 MUST 将阶段恢复为 `analysis_running` 并恢复轮询

#### Scenario: Page reload after completed task
- **WHEN** 用户刷新页面且最新 annotation_kinematics 任务已完成
- **THEN** 系统 MUST 将阶段恢复为 `report_ready` 并展示报告入口

### Requirement: Primary flow fixes to side camera and CVAT
主流程 SHALL 仅突出侧面机位，并将主标注入口固定为 CVAT Skeleton XML（`.xml`）。正面、俯视、水下、半水下 SHALL 作为只读的"后续扩展机位"区域，不提供上传按钮且不影响当前工作流就绪状态。

#### Scenario: Non-side cameras are non-interactive
- **WHEN** 用户查看后续扩展机位区域
- **THEN** 系统 MUST NOT 显示上传按钮
- **AND** 已有非侧面视频仅以只读素材展示

#### Scenario: Primary annotation source restricted
- **WHEN** 用户选择标注文件
- **THEN** 系统 MUST 仅允许 `source=cvat` 且具有有效 parsed 状态、side 视角、非空 normalized_annotation_id 的标注被选择

### Requirement: Resubmit reuses submit endpoint with concurrency guard
系统 SHALL 通过 `POST /analysis/submit` 复用实现 `resubmit`（用当前标注 id 与 revision 新建任务），并在同一 TrainingSession 下仅允许一个活跃 `annotation_kinematics` 任务。

#### Scenario: Concurrent active task prevented
- **WHEN** 用户针对已有活跃 annotation_kinematics 任务（queued/processing/result_saving）的 session 再次提交
- **THEN** 系统 MUST 返回 HTTP 409 `ANALYSIS_TASK_ALREADY_ACTIVE`
- **AND** 响应 MUST 包含 `existing_task_id`
- **AND** MUST NOT 创建第二个任务

#### Scenario: Resubmit after revision drift
- **WHEN** 失败原因为输入/版本类错误（如 ANNOTATION_REVISION_DRIFT）
- **THEN** 前端 MUST 调用 `POST /analysis/submit` 以当前 annotation id 与 revision 创建新任务而非 `retry`

### Requirement: Report freshness is orthogonal to workflow phase
系统 SHALL 将报告新鲜度（`none`/`current`/`stale`）作为与工作流阶段正交的属性，不引入额外工作流阶段。

#### Scenario: Completed report based on older annotation revision
- **WHEN** 最新完成任务基于 rev3 而当前选中标注为 rev4
- **THEN** 系统 MUST 将 `workflow_phase` 保持为 `report_ready`
- **AND** `report_freshness` MUST 为 `stale`
- **AND** UI MUST 显示 stale 警告与重新生成动作
