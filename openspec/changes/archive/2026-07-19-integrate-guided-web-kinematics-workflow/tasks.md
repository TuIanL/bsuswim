## 1. 后端读取契约：并发防重

- [x] 1.1 在 `create_analysis_task()` 中增加活跃 annotation 任务解析：匹配同一 `session_id`、`pipeline_type=annotation_kinematics`、`status ∈ {queued, processing, result_saving}`
- [x] 1.2 在检查与创建前用 `with_for_update()` 锁定 TrainingSession 行，避免并发穿透
- [x] 1.3 定义领域异常 `AnalysisTaskAlreadyActiveError(existing_task_id)`，service 命中活跃任务时 `raise`
- [x] 1.4 在 submit 路由中将 `AnalysisTaskAlreadyActiveError` 映射为 HTTP 409 `ANALYSIS_TASK_ALREADY_ACTIVE`，detail 含 `existing_task_id`（不在此前由 service 直接返回 HTTP）
- [x] 1.5 确保该防护不影响既有 `model_service` 任务

## 2. 后端读取契约：标注列表投影

- [x] 2.1 扩展 `AnnotationFileListItem`：新增 `parse_summary`、`quality`、`kinematics_module_readiness`，保留现有 `quality_status` 与 `analysis_readiness`
- [x] 2.2 实现轻量 parse-summary 投影：事件数、keypoint 帧数、轨迹数、人工标签数（列表响应不返回完整帧数组）
- [x] 2.3 实现四类模块 annotation-readiness 投影（`body_posture`/`upper_limb`/`lower_limb`/`head_trunk`，状态 ready|degraded|blocked）：采用"最差状态"合并——`body_posture ← body_position`、`upper_limb ← worse(arm_entry, catch_pull)`、`lower_limb ← worse(leg_kick, efficiency)`、`head_trunk` 由头部关键点相关 issue 推导，无判断依据时默认 degraded（禁止无说明默认 ready）；注明这是分析前就绪状态而非最终报告可用性

## 3. 后端读取契约：统一流水线进度

- [x] 3.1 在 `checkpoints.py` 中导出规范有序阶段定义 `ANNOTATION_KINEMATICS_STAGE_SPECS`，并定义 `PIPELINE_STAGE_SPECS` 注册表（`annotation_kinematics` / `model_service`），未命中规范的 pipeline 不虚构步骤
- [x] 3.2 定义 `PipelineStepRead` 与 `PipelineProgressRead`
- [x] 3.3 实现 `build_pipeline_progress(task)`：按 D18 算法投影——completed 全 completed、processing 当前前 completed/当前 running/后续 pending、failed 失败前 completed/失败 failed/后续 pending；steps 已有真实状态优先；保留 warnings 与 attempt_count
- [x] 3.4 实现公共投影 `build_analysis_common_payload(task)` 与两个独立 serializer `read_analysis_task(task)` / `read_analysis_status(task)`，二者均复用 3.3 与 `task_actions(task)`（不强行让一个函数构造两个不同 response model）
- [x] 3.5 为 `AnalysisTaskRead` 与 `AnalysisStatusRead` 增加 `pipeline_progress` 与 `actions` 字段
- [x] 3.6 用公共投影替换列表、详情、status 三条路由各自手写的响应（status 路由需补齐真实 `pipeline_type/version/attempt_count/failed_stage/error_code/actions`）
- [x] 3.7 原始 `execution_state` 保留为内部持久化结构，不作为前端主契约

## 4. 后端读取契约：失败动作分类与按 session 查询

- [x] 4.1 在 `analysis_pipelines/errors.py` 定义集中 `ERROR_RECOVERY_POLICY` 注册表，覆盖真实错误码：输入/版本类（INVALID_INPUT/ANNOTATION_NOT_FOUND/ANNOTATION_REVISION_DRIFT/SESSION_MISMATCH/UNSUPPORTED_VIEW/NO_KEYPOINT_FRAMES）→ resubmit；执行阶段类（METRIC_PERSIST_FAILED/METRIC_REVISION_MISMATCH/ARTIFACT_GENERATION_FAILED/REVIEW_FINDINGS_GENERATION_FAILED/REPORT_ASSEMBLY_FAILED/PIPELINE_INTERNAL_ERROR）→ retry；非用户可恢复（UNSUPPORTED_PIPELINE_VERSION/TASK_OWNER_UNAVAILABLE）→ details
- [x] 4.2 改造 `task_actions(task)` 改为查表：resubmit 类且为 annotation pipeline 失败 → `["resubmit","details"]`；retry 类 → `["retry","details"]`；details 类或未知 → `["details"]`；completed → `["workspace","report"]`
- [x] 4.3 非 annotation pipeline 行为仍走注册表（legacy 默认 details）
- [x] 4.4 扩展 `GET /analysis`：支持 `session_id`、`pipeline_type=annotation_kinematics`、`limit`，排序固定 `updated_at DESC`，保留现有无过滤行为

## 5. 后端读取契约：重解析验证

- [x] 5.1 验证并记录现有 `POST /annotations/{annotation_file_id}/parse` 的重解析行为（不新增端点）
- [x] 5.2 确保已持久化且归属当前用户的标注文件可重复解析
- [x] 5.3 确保解析成功后更新当前 NormalizedAnnotation 的 `revision`
- [x] 5.4 确保响应返回 parse summary、quality 与 readiness
- [x] 5.5 增加重解析归属与失败响应的契约测试

## 6. 前端类型与 API 对齐

- [x] 6.1 扩展标注类型：`AnnotationQualityReport`、`QualityIssue`、`ModuleReadiness`、`KinematicsModuleReadiness`、`parse_summary`
- [x] 6.2 扩展分析任务类型：`pipeline_type`、`pipeline_version`、`attempt_count`、`failed_stage`、`error_code`、`pipeline_progress`
- [x] 6.3 扩展 `submitAnalysis()`：接受 `pipeline_type` 与 `pipeline_version`
- [x] 6.4 增加 `retryAnalysisTask(taskId)`
- [x] 6.5 增加 `reparseAnnotation(annotationFileId, options)`（复用现有 parse 端点，不要求重传文件）
- [x] 6.6 扩展 `listTasks()`：支持 session、pipeline、limit 过滤
- [x] 6.7 增加前端阶段中文标签映射；渲染步骤严格按 `pipeline_progress.steps` 返回的顺序；前端 SHALL NOT 维护独立的规范阶段顺序（顺序归后端，见 D18/D19）

## 7. 工作流状态模型

- [x] 7.1 新增 `useKinematicsWorkflow.ts`
- [x] 7.2 在安全的范围内并行加载：Session、Athlete、Session videos、side 标注文件、最新 annotation 任务
- [x] 7.3 根据服务端数据推导当前 `WorkflowPhase`
- [x] 7.4 刷新后恢复选中标注：优先 active 任务所用标注，否则最新可提交标注，绝不选中 invalid 标注
- [x] 7.5 依据 `ReportMetadata.task_id` 所指任务的 annotation id 与 revision 检测报告新鲜度（`ReportFreshness = none|current|stale`），而非独立选最新 completed task
- [x] 7.6 仅当最新任务处于 queued/processing 时轮询
- [x] 7.7 任务 completed 或 failed 时停止轮询

## 8. 侧面视频步骤

- [x] 8.1 用单一 side-video 卡片替换五机位主网格
- [x] 8.2 保留上传与 session-video 绑定行为
- [x] 8.3 展示文件名、文件大小、FPS、分辨率、绑定状态
- [x] 8.4 允许在显式确认下替换当前侧面视频
- [x] 8.5 绑定侧面视频前阻断后续步骤

## 9. CVAT 标注步骤

- [x] 9.1 将主标注入口固定为 `cvat`，文件选择器限制 `.xml`
- [x] 9.2 将 CTA 改名为"上传 CVAT 骨架标注"
- [x] 9.3 展示不确定进度态：上传中 / 解析中 / 质量检查中
- [x] 9.4 成功后展示 parse summary
- [x] 9.5 列出已有标注：文件名、revision、解析状态、质量状态、上传时间
- [x] 9.6 为持久化 `parse_failed` 文件提供"重新解析"动作（调用 `reparseAnnotation`）
- [x] 9.7 为 invalid 标注提供替换上传动作

## 10. 质量与模块就绪步骤

- [x] 10.1 新增 `AnnotationQualityPanel`
- [x] 10.2 展示整体状态、质量分数、blocking/warning/info 数量
- [x] 10.3 按严重级别分组质量问题，优先展示 `user_message`
- [x] 10.4 在提供时展示建议操作标签
- [x] 10.5 新增四张模块卡片（身体姿态/上肢/下肢/头躯干），使用 ready|degraded|blocked 一致状态
- [x] 10.6 warning 标注提交前需显式确认；invalid 标注禁用报告生成

## 11. 分析提交与进度

- [x] 11.1 将通用"提交分析"改为"生成二维运动学报告"
- [x] 11.2 提交前置条件：已绑定 side 视频 + 已选 normalized annotation + `analysis_readiness.can_submit=true` + 无活跃 annotation pipeline 任务
- [x] 11.3 显式提交 `annotation_kinematics` / `side_2d_v1`
- [x] 11.4 任务创建后停留在当前工作流页
- [x] 11.5 新增 `AnalysisProgressPanel`，渲染真实流水线步骤序列
- [x] 11.6 每步标记 pending/running/completed/failed，展示后端进度百分比与 attempt count
- [x] 11.7 展示 execution state 中的 pipeline warnings

## 12. 失败与恢复

- [x] 12.1 以用户语言展示失败阶段
- [x] 12.2 单独展示 error_code（区别于用户文案）
- [x] 12.3 仅当 `actions` 含 `retry` 时显示"重试当前任务"
- [x] 12.4 仅当 `actions` 含 `resubmit` 时显示"使用当前标注重新生成"
- [x] 12.5 resubmit：刷新标注列表、选中当前 revision、新建分析任务
- [x] 12.6 重试后保留上一次失败详情
- [x] 12.7 重试/resubmit 进行中禁止重复点击
- [x] 12.8 收到 409 `ANALYSIS_TASK_ALREADY_ACTIVE` 时直接绑定并恢复 `existing_task_id` 进度

## 13. 报告就绪步骤

- [x] 13.1 检测已完成且当前 ReportMetadata 真实存在的 annotation pipeline 任务（报告 API 404 时复用 `analysis_failed` + 合成错误 `REPORT_METADATA_MISSING`，提供刷新/重新生成）
- [x] 13.2 展示报告完成摘要
- [x] 13.3 提供"查看 HTML 报告"（复用 `/reports/:sessionId`，以 ReportMetadata.task_id 为权威）
- [x] 13.4 复用现有 PDF status API，支持导出/下载/重导出过期 PDF/重试失败导出
- [x] 13.5 当选中标注 revision 与 ReportMetadata.task_id 所指任务不一致时显示 stale 报告警告
- [x] 13.6 不在工作流页复制报告 section 渲染

## 14. 后续扩展机位

- [x] 14.1 新增折叠的 `FutureCameraViewsPanel`
- [x] 14.2 以禁用路线图卡片展示四个非 side 视角
- [x] 14.3 说明每个未来视角的能力意图
- [x] 14.4 以只读素材展示已有非 side 上传
- [x] 14.5 确保它们永不影响当前工作流就绪状态

## 15. 工作台兼容

- [x] 15.1 识别 `swim-analysis.annotation-kinematics.v1`
- [x] 15.2 对 annotation pipeline 结果不再显示 schema 不兼容警告
- [x] 15.3 不将空 annotation-pipeline keypoint frames 传入旧 OverlayCanvas
- [x] 15.4 展示任务步骤、质量摘要与报告入口
- [x] 15.5 保留旧 model-service 工作台行为

## 16. 测试

- [x] 16.1 后端：标注列表返回 parse 与 quality 摘要
- [x] 16.2 后端：任务 status 返回真实 pipeline 元数据与 `pipeline_progress`
- [x] 16.3 后端：analysis list 过滤生效
- [x] 16.4 后端：可重试的执行失败暴露 `retry`
- [x] 16.5 后端：revision drift 暴露 `resubmit`
- [x] 16.6 后端：并发提交返回 409 且含 `existing_task_id`；至少一项在 PostgreSQL 环境下用两个并发事务验证，断言仅创建一个任务且另一请求收到 `existing_task_id`（SQLite 行锁语义不能完全代表生产库，单线程 service test 不足以证明并发穿透被阻止）
- [x] 16.7 后端：同一文件重复解析与重解析归属/失败响应
- [x] 16.8 前端：无 side 视频映射到步骤 1
- [x] 16.9 前端：有 side 视频无标注映射到步骤 2
- [x] 16.10 前端：有效标注启用生成
- [x] 16.11 前端：warning 标注需确认、invalid 标注阻断生成
- [x] 16.12 前端：运行中任务刷新后恢复
- [x] 16.13 前端：失败任务展示失败阶段与正确动作
- [x] 16.14 前端：完成任务暴露报告动作
- [x] 16.15 前端：非 side 机位保持非交互
- [x] 16.16 E2E：创建 session → 上传 side 视频 → ingest CVAT XML → 确认模块就绪 → 提交 annotation pipeline → 观察全部流水线阶段 → 打开 HTML 报告 → 导出/下载 PDF

## 17. 文档与验证

- [x] 17.1 说明六步用户工作流
- [x] 17.2 说明 annotation readiness / metric availability / report availability 三者区别
- [x] 17.3 说明 retry 与 resubmit 语义
- [x] 17.4 运行后端测试
- [x] 17.5 运行前端类型检查与构建
- [x] 17.6 验证现有 ReportView 与 PDF 导出未被修改
