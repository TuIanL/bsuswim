# Tasks: Add Annotation-Driven Analysis Pipeline

## 1. Baseline and contracts

- [x] 1.1 记录现有 model_service task 行为的回归测试
- [x] 1.2 记录当前 annotation snapshot 的 request_payload 契约
- [x] 1.3 确认以下服务可独立调用：
  - calculate_and_persist
  - kinematic_artifacts.generate
  - generate_review_findings
  - assemble_five_page_kinematics_report
- [x] 1.4 为同一输入重复调用建立幂等基线测试
- [x] 1.5 确认现有全部后端测试通过

## 2. AnalysisTask persistence

- [x] 2.1 新增 pipeline_type
- [x] 2.2 新增 pipeline_version
- [x] 2.3 新增 execution_state JSON
- [x] 2.4 新增 attempt_count
- [x] 2.5 新增 failed_stage
- [x] 2.6 新增 error_code
- [x] 2.7 编写 Alembic migration
- [x] 2.8 为现有任务回填 model_service / model_service_v1
- [x] 2.9 更新 AnalysisTaskRead 和 AnalysisStatusRead

## 3. Submission and routing

- [x] 3.1 扩展 AnalysisSubmit.pipeline_type
- [x] 3.2 扩展 AnalysisSubmit.pipeline_version
- [x] 3.3 实现 resolved pipeline type 规则
- [x] 3.4 normalized_annotation_id 存在且未显式指定时选择 annotation_kinematics
- [x] 3.5 无 annotation 输入时保持 model_service
- [x] 3.6 hybrid 返回 PIPELINE_NOT_IMPLEMENTED
- [x] 3.7 annotation_kinematics 缺少 annotation ID 时拒绝提交
- [x] 3.8 在 analysis_input 中保存 session_video_id 和 video_file_id
- [x] 3.9 保留质量 warning acknowledgement 快照
- [x] 3.10 pipeline_version 为空时按类型默认：annotation_kinematics→side_2d_v1，model_service→model_service_v1
- [x] 3.11 pipeline_type 与 pipeline_version 不匹配（如 model_service+side_2d_v1）在提交时拒绝，返回 UNSUPPORTED_PIPELINE_VERSION

## 4. Pipeline framework

- [x] 4.1 新增统一的 async AnalysisPipeline protocol（run 为 async def）
- [x] 4.2 新增 PipelineOutcome
- [x] 4.3 新增 PipelineExecutionError
- [x] 4.4 新增 pipeline registry（统一 resolve，不再按类型分派）
- [x] 4.5 将现有 model service 执行提取为 ModelServicePipeline（async run 内部 await 客户端）
- [x] 4.6 保证 model_service 回归行为不变
- [x] 4.7 dispatcher 统一为 `await registry.resolve(task.pipeline_type).run(task.id, task.pipeline_version)`
- [x] 4.8 AnnotationKinematicsPipeline.run 内部 `await run_in_threadpool(self._run_sync, ...)`，不再由 dispatcher 判断
- [x] 4.9 每个 pipeline 在线程或协程内部独立管理 DB Session
- [x] 4.10 Keep `ModelServicePipeline` on the existing
           `_set_task_state` / `_mark_failed` behavior
- [x] 4.11 Do not retrofit annotation checkpoint semantics into the legacy
           model-service failure helpers
- [x] 4.12 Add regression tests proving model-service stage, progress and
           error-message behavior remain unchanged

## 5. Task claim and checkpoint support

- [x] 5.1 实现数据库行锁 claim
- [x] 5.2 防止同一 task 被重复并发执行
- [x] 5.3 实现 attempt_count
- [x] 5.4 实现 execution_state 初始结构
- [x] 5.5 实现 step running/completed/failed checkpoint
- [x] 5.6 JSON 更新使用重新赋值，避免 dirty tracking 失效
- [x] 5.7 实现结构化 error_code / failed_stage
- [x] 5.8 保证 progress 单调递增
- [x] 5.9 Add a dedicated `PipelineTaskStateWriter` for
          annotation-kinematics tasks
- [x] 5.10 Ensure annotation failures persist `failed_stage`, `error_code`
           and the failed step before setting the public stage to `failed`
- [x] 5.11 Verify model-service tasks may leave the new structured fields
           null or empty without affecting API compatibility

## 6. Input validation stage

- [x] 6.1 只从 task snapshot 读取 annotation ID
- [x] 6.2 校验 annotation 存在
- [x] 6.3 校验 revision 精确匹配
- [x] 6.4 校验 session 归属
- [x] 6.5 校验 session_video 和 video_file
- [x] 6.6 校验 view_type = side
- [x] 6.7 校验 keypoint_frames 非空
- [x] 6.8 校验质量状态和 warning acknowledgement
- [x] 6.9 校验 pipeline_version = side_2d_v1
- [x] 6.10 revision drift 返回 ANNOTATION_REVISION_DRIFT
- [x] 6.11 Resolve the pipeline owner from `task.session.coach_id`
- [x] 6.12 Pass the resolved `User` to review-findings and report-assembly services
- [x] 6.13 Fail with `TASK_OWNER_UNAVAILABLE` when the persisted owner cannot be resolved

## 7. Metrics stage

- [x] 7.1 调用 side_2d_kinematics calculator
- [x] 7.2 persist=True
- [x] 7.3 保存 annotation_metric_id checkpoint
- [x] 7.4 校验 source_revision
- [x] 7.5 校验 calculator/schema
- [x] 7.6 测试重复运行复用同一 AnnotationMetric
- [x] 7.7 测试不调用 ModelServiceClient

## 8. Artifact stage

- [x] 8.1 调用 kinematic artifact generation service
- [x] 8.2 保存 artifact_set_id 和 generation_signature
- [x] 8.3 ready set 直接复用
- [x] 8.4 partial set 直接复用
- [x] 8.5 retry 时对 failed set 使用 force=true
- [x] 8.6 failed/partial 状态允许后续报告降级
- [x] 8.7 系统异常写入 ARTIFACT_GENERATION_FAILED

## 9. Review findings stage

- [x] 9.1 调用 side_2d_kinematics_v1 规则集
- [x] 9.2 保存 finding_set_id 和 generation_signature
- [x] 9.3 ready set 直接复用（KinematicReviewFindingSet 无 failed 状态，默认 ready）
- [x] 9.4 空 findings 视为有效 ready 结果
- [x] 9.5 不写成确定性 diagnostics
- [x] 9.6 规则执行异常写入 REVIEW_FINDINGS_GENERATION_FAILED
- [x] 9.7 findings force 策略对齐 artifacts：expected-signature set 不存在→force=false；ready→复用；retry（attempt_count>1）时重新执行（异常不残留可复用记录）

## 10. AnalysisResult stage

- [x] 10.1 定义 swim-analysis.annotation-kinematics.v1
- [x] 10.2 按 task_id 创建或更新 AnalysisResult
- [x] 10.3 metrics 保存任务指标快照
- [x] 10.4 diagnostics 保持空列表
- [x] 10.5 raw_result 保存 product IDs 和 pipeline trace
- [x] 10.6 不复制 keypoint_frames 和视频检测数据
- [x] 10.7 保存 analysis_result_id checkpoint

## 11. Quality summary

- [x] 11.1 不直接使用旧指标键的聚合映射
- [x] 11.2 新增专用 `aggregate_side_2d_kinematics_quality(annotation_quality, metric_quality)` 适配器（不在旧 AnalysisQualityAggregator 上加 profile）
- [x] 11.3 将 Side2DKinematicsQualityEvaluator 的 issue 列表桥接到四个报告模块 body_posture / upper_limb / lower_limb / head_trunk（显式映射 annotation 的 5 模块键 → 报告 4 模块键）
- [x] 11.4 输出 full / degraded / blocked
- [x] 11.5 将质量快照写入 AnalysisResult.quality_summary
- [x] 11.6 low_confidence 不得提升为确定性结论

## 12. Five-page report assembly

- [x] 12.1 调用 assemble_five_page_kinematics_report
- [x] 12.2 修复 assembly service 的宽泛 except Exception
- [x] 12.3 仅 review_findings_not_generated 可降级
- [x] 12.4 stale / schema / config 错误正常抛出
- [x] 12.5 向 report_data 写入稳定的 source_trace（含 annotation/metric/artifact/finding/报告签名），不在报告内容中放 task_id / analysis_result_id / attempt
- [x] 12.6 校验固定五页顺序
- [x] 12.7 校验 generation_signature（相同签名对应相同 report_data）
- [x] 12.8 保存 assembly_status 和 warnings

## 13. ReportMetadata persistence

- [x] 13.1 按 session_id 查找当前 ReportMetadata
- [x] 13.2 不存在时创建
- [x] 13.3 存在时整体替换 report_data
- [x] 13.4 source 设置为 annotation_kinematics
- [x] 13.5 task_id 更新为当前 task
- [x] 13.6 generated_at 显式刷新
- [x] 13.7 exported PDF 标记为 stale
- [x] 13.8 相同 generation_signature 不重复改写内容
- [x] 13.9 保存 report_id checkpoint
- [x] 13.10 报告持久化前先取得 session 行锁（SELECT ... FOR UPDATE）
- [x] 13.11 防止不同 task 并发首写撞 session_id 唯一约束
- [x] 13.12 验证 last committed successful report 成为当前报告（同 session 多 pipeline）

## 14. Completion and failure handling

- [x] 14.1 完成时 task.status = completed
- [x] 14.2 完成时 task.stage = completed
- [x] 14.3 完成时 progress = 100
- [x] 14.4 更新 completed_at
- [x] 14.5 完成时通过 `refresh_session_analysis_status(session_id)` 推导 TrainingSession.status（不直接无条件写）
- [x] 14.6 失败时记录 failed_stage
- [x] 14.7 失败时记录 error_code 和 error_message
- [x] 14.8 失败时通过 `refresh_session_analysis_status` 推导状态（非无条件写 failed）
- [x] 14.9 partial report 不将 task 标记为 failed
- [x] 14.10 失败处理先 `db.rollback()` 再记录失败，failure recorder 使用独立 SessionLocal 以防 PendingRollbackError
- [x] 14.11 验证工作 session 损坏时任务仍能进入稳定 failed 状态

## 15. Retry API

- [x] 15.1 新增 POST /analysis/{task_id}/retry
- [x] 15.2 校验任务所有权
- [x] 15.3 仅允许 failed 且 pipeline_type == annotation_kinematics 的 task（model_service 不在本 Change 支持 retry）
- [x] 15.4 重置 queued 状态
- [x] 15.5 保存 previous failure 到 execution_state
- [x] 15.6 重新加入 BackgroundTasks
- [x] 15.7 重试仍使用原 annotation ID + revision
- [x] 15.8 revision drift 时拒绝继续
- [x] 15.9 验证 metrics/artifacts/findings 复用行为
- [x] 15.10 验证 model_service task 的既有 actions 不受影响

## 16. API and status compatibility

- [x] 16.1 AnalysisTaskRead 返回 pipeline_type/version
- [x] 16.2 AnalysisStatusRead 返回 pipeline_type/version
- [x] 16.3 返回 attempt_count、failed_stage、error_code
- [x] 16.4 保持旧 actions 字段兼容
- [x] 16.5 failed task actions 包含 retry
- [x] 16.6 completed task actions 包含 report
- [x] 16.7 model_service API 契约不变

## 17. Unit tests

- [x] 17.1 pipeline routing tests
- [x] 17.2 annotation input validation tests
- [x] 17.3 revision drift tests
- [x] 17.4 stage transition tests
- [x] 17.5 progress monotonicity tests
- [x] 17.6 execution_state dirty tracking tests
- [x] 17.7 retry force policy tests
- [x] 17.8 AnalysisResult upsert tests
- [x] 17.9 ReportMetadata replacement tests
- [x] 17.10 PDF stale tests
- [x] 17.11 assembly exception classification tests
- [x] 17.12 model_service regression tests

## 18. Integration and E2E tests

- [x] 18.1 真实 CVAT fixture → annotation pipeline
- [x] 18.2 生成 side_2d_kinematics AnnotationMetric
- [x] 18.3 生成五类 artifacts
- [x] 18.4 生成 review findings
- [x] 18.5 创建 AnalysisResult
- [x] 18.6 创建或更新 ReportMetadata
- [x] 18.7 报告严格包含五页
- [x] 18.8 报告来源为 annotation_kinematics
- [x] 18.9 断言 ModelServiceClient 未被调用
- [x] 18.10 第二次执行不产生重复产物
- [x] 18.11 中间故障后 retry 成功
- [x] 18.12 标注 revision 变化后旧任务拒绝重跑
- [x] 18.13 artifacts partial 时任务完成、报告 partial
- [x] 18.14 空 findings 时任务完成

## 19. OpenSpec and documentation

- [x] 19.1 新增 annotation-driven-analysis-pipeline spec
- [x] 19.2 修改 heavy-model-analysis-architecture spec
- [x] 19.3 修改 five-page-kinematics-report spec
- [x] 19.4 修改 report-data-assembly spec
- [x] 19.5 记录 pipeline_type/version 契约
- [x] 19.6 记录 execution_state schema
- [x] 19.7 记录错误码
- [x] 19.8 记录 retry 与 revision drift 行为
- [x] 19.9 更新后端 API 文档

## 20. 六项关键决策的落地任务

- [x] 20.1 实现统一 async AnalysisPipeline protocol 与 registry.resolve，dispatcher 不再按类型分派（对应 design §5/§6）
- [x] 20.2 实现 `aggregate_side_2d_kinematics_quality` 专用适配器，桥接 evaluator issue → 4 报告模块（对应 design §14）
- [x] 20.3 报告内容只写入稳定 source_trace，task/result/attempt 引用移出 report_data（对应 design §15）
- [x] 20.4 实现 `refresh_session_analysis_status(db, session_id)` 状态聚合器，annotation pipeline 经它写 session 状态（对应 design §19）
- [x] 20.5 报告持久化前取得 session 行锁，保证同 session 多 pipeline 串行（对应 design §21）
- [x] 20.6 失败处理先 rollback 再用独立 session 记录失败，杜绝 PendingRollbackError 卡在 processing（对应 design §20）
- [x] 20.7 retry 仅对 annotation_kinematics 开放，model_service 既有 actions 不变（对应 design §17）
- [x] 20.8 pipeline_version 默认与不匹配组合在提交时拒绝（对应 design §4 / tasks 3.10–3.11）

## 21. 扩展测试（覆盖六项决策）

- [x] 21.1 async protocol：两种 pipeline 均经统一 `await pipeline.run(...)` 调度
- [x] 21.2 质量适配器：issue → 4 模块映射与 full/degraded/blocked 输出正确
- [x] 21.3 相同 generation_signature 重试时 report_data 内容不变、source_trace 不变
- [x] 21.4 多任务 session：annotation 完成 + model_service 失败后 TrainingSession 仍为 completed
- [x] 21.5 并发首写：两 task 同 session 不撞唯一约束，最终仅一个 current report
- [x] 21.6 工作 session 损坏后任务仍进入 failed 而非 stuck processing
- [x] 21.7 model_service task 不支持 retry，annotation_kinematics 支持
- [x] 21.8 不匹配 pipeline_type/version 组合在提交时 422
