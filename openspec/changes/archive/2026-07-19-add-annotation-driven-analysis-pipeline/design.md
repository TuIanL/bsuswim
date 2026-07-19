# Design: Add Annotation-Driven Analysis Pipeline

## 1. Context

AnalysisTask 当前已经保存：

request_payload.analysis_input.annotation_id
request_payload.analysis_input.annotation_revision
request_payload.analysis_input.annotation_quality_snapshot

但 run_analysis_task() 不读取 analysis_input.type，而是固定执行：

ModelServiceClient.analyze()
  → save_analysis_result()
  → legacy build_report_data()

与此同时，annotation_kinematics 所需的四个服务已经独立存在：

1. calculate_and_persist()
2. kinematic_artifacts.generate()
3. generate_review_findings()
4. assemble_five_page_kinematics_report()

Change 7 的职责是引入任务级编排层，而不是重新实现这些服务。

代码核对事实（2026-07-18）：

- `backend/app/services/analysis_service.py:204` 的 `run_analysis_task` 无条件构建
  `ModelAnalysisRequest` 并调用 `ModelServiceClient.analyze()`，提交阶段写入的
  `analysis_input` 快照（analysis_service.py:156）从未被回读。
- 四个下游服务的签名已存在且可由 pipeline 直接调用：
  - `metrics_service.calculate_and_persist(db, normalized_annotation_id, *, persist, current_user_id, calculator)`
  - `kinematic_artifacts.generation_service.generate(db, annotation_metric_id, *, force, current_user_id) -> (KinematicArtifactSet, bool)`
  - `diagnostics.review_findings.generation_service.generate_review_findings(db, annotation_metric_id, current_user, rule_set, force) -> (KinematicReviewFindingSet, bool)`
  - `reporting.kinematics_report.assembly_service.assemble_five_page_kinematics_report(db, annotation_metric_id, current_user) -> FivePageKinematicsReport`
  - 最后一个服务注释明确声明：`This service does NOT persist ReportMetadata (reserved for Change 7)`

部分校验已由下游服务自身完成，pipeline 不必重复：
- `calculate_and_persist` 已对 `view_type != "side"` 与空 `keypoint_frames` 抛错。
- `generate` 已按 `generation_signature` 自管理 upsert 与 force 重建。
- `generate_review_findings` 已对 `invalid_rule_set` / `rule_output_kind_mismatch`
  抛出结构化 `ReviewFindingsGenerationError`。
pipeline 仍需自行校验：revision 精确匹配、session 归属、质量状态、warning 确认、
以及 `pipeline_version == side_2d_v1`。

## 2. 先拍板几个关键设计

### 2.1 不重写现有产品服务，只做编排

Annotation pipeline 不重新实现任何算法，而是依次调用：

calculate_and_persist()
generate()
generate_review_findings()
assemble_five_page_kinematics_report()

Change 7 只负责：

输入锁定
任务路由
阶段状态
错误处理
幂等恢复
AnalysisResult 快照
ReportMetadata 持久化

### 2.2 AnalysisTask.status 不扩成九种状态

现有状态枚举继续保留：

queued
processing
result_saving
completed
failed

具体执行阶段继续使用字符串字段 `stage`。现有模型本身已经把“总体状态”和“具体阶段”分开，因此不需要修改 PostgreSQL Enum。

### 2.3 AnalysisResult 是流水线执行收据，不是新的事实源

权威数据仍然分别位于：

AnnotationMetric
KinematicArtifactSet
KinematicReviewFindingSet
ReportMetadata

`AnalysisResult` 保存兼容性快照和这些产物的引用，不应成为第四套指标、图表和 findings 数据库。

建议：

schema_version = swim-analysis.annotation-kinematics.v1
metrics        = AnnotationMetric.metrics 的任务快照
diagnostics    = []  # review findings 不冒充确定性 diagnostics
raw_result     = pipeline 与各产物的追溯信息
quality_summary = 标注质量 + 指标质量聚合

### 2.4 retry 重跑同一个任务，不创建新任务

同一个任务已经锁定了 annotation ID 和 revision。失败后重跑同一个 task，才能自然复用已生成的 metric、artifact 和 finding set。

标注 revision 已变化时，不允许重跑旧任务，必须返回输入过期错误并重新提交。

### 2.5 五页报告直接替换当前 session 报告

`ReportMetadata` 当前是“一条 session 对应一条报告”，由 `session_id` 唯一约束保证。Annotation pipeline 完成后，应将这条记录整体更新为当前五页报告，不与旧 mock 报告字段混合。

### 2.6 必须修正 assembly service 的异常吞噬

当前 assembly service 对 `get_current_review_findings()` 使用了宽泛的 `except Exception`，任何 stale、规则配置或数据库问题都会被静默当成“没有 findings”。

本 Change 应改为：

review_findings_not_generated
→ 允许 partial report

metric_revision_stale
invalid_rule_set
rule_output_kind_mismatch
其他系统异常
→ 正常向上抛出，不得静默降级

## 3. AnalysisTask 持久化字段

建议新增：

class AnalysisTask:
    pipeline_type: str
    pipeline_version: str

    execution_state: dict
    attempt_count: int

    failed_stage: str | None
    error_code: str | None

不建议使用数据库 Enum 保存 `pipeline_type`，使用普通 `VARCHAR`：

model_service
annotation_kinematics
hybrid

原因是未来新增泳姿、机位或融合 pipeline 时，不应每次修改 PostgreSQL enum。

初始 migration：

ALTER TABLE analysis_tasks
ADD COLUMN pipeline_type VARCHAR(40) NOT NULL DEFAULT 'model_service',
ADD COLUMN pipeline_version VARCHAR(50) NOT NULL DEFAULT 'model_service_v1',
ADD COLUMN execution_state JSON NOT NULL DEFAULT '{}',
ADD COLUMN attempt_count INTEGER NOT NULL DEFAULT 0,
ADD COLUMN failed_stage VARCHAR(80),
ADD COLUMN error_code VARCHAR(100);

`request_payload` 继续表示不可变的提交输入，`execution_state` 表示可变执行状态，二者不能混用。

## 4. Pipeline 路由规则

## Decision: Explicit routing with backward-compatible inference

执行类型按以下优先级解析：

1. payload.pipeline_type 显式提供
2. 未提供 pipeline_type，但 normalized_annotation_id 不为空
   → annotation_kinematics
3. 两者都未提供
   → model_service

annotation_kinematics 仅接受：

pipeline_version = side_2d_v1

hybrid 在本 Change 中属于已知但未实现的 pipeline，
提交时返回 422 PIPELINE_NOT_IMPLEMENTED。

系统不得在 annotation_kinematics 失败后静默回退到 model_service。

建议扩展提交结构：

class AnalysisSubmit(BaseModel):
    session_id: int
    normalized_annotation_id: int | None = None
    acknowledge_quality_warnings: bool = False

    pipeline_type: Literal[
        "model_service",
        "annotation_kinematics",
        "hybrid",
    ] | None = None

    pipeline_version: str | None = None

任务创建后将解析出的类型写入独立字段，同时保存：

{
  "analysis_input": {
    "type": "normalized_annotation",
    "annotation_id": 401,
    "annotation_revision": 3,
    "session_video_id": 201,
    "video_file_id": 101,
    "annotation_quality_snapshot": {},
    "quality_warning_acknowledged": true
  }
}

## 5. Pipeline 接口

## Decision: All pipelines expose a single async protocol

registry 中的 pipeline 必须实现同一个 `async def run(...)`，dispatcher 不再
按具体类型分派。同步阻塞工作（SQLAlchemy / OpenCV / 文件渲染）由 pipeline
内部通过 `run_in_threadpool` 下沉，而不是由 dispatcher 判断。

class AnalysisPipeline(Protocol):
    pipeline_type: str
    supported_versions: set[str]

    async def run(
        self,
        task_id: int,
        pipeline_version: str,
    ) -> PipelineOutcome:
        ...

实现方式：

class ModelServicePipeline:
    async def run(self, task_id, pipeline_version) -> PipelineOutcome:
        return await self._run_model_service(task_id, pipeline_version)

class AnnotationKinematicsPipeline:
    async def run(self, task_id, pipeline_version) -> PipelineOutcome:
        return await run_in_threadpool(
            self._run_sync, task_id, pipeline_version
        )

dispatcher 因此统一为：

pipeline = registry.resolve(task.pipeline_type)
outcome = await pipeline.run(task.id, task.pipeline_version)

注意：AnnotationKinematicsPipeline 在线程内部必须创建并关闭自己的
`SessionLocal()`，不得跨线程复用路由层 Session（见 §6）。

建议目录：

backend/app/services/analysis_pipelines/
├── __init__.py
├── protocols.py
├── registry.py
├── context.py
├── model_service.py
├── annotation_kinematics.py
├── checkpoints.py
└── errors.py

registry：

PIPELINE_REGISTRY = {
    "model_service": ModelServicePipeline(),
    "annotation_kinematics": AnnotationKinematicsPipeline(),
}

`hybrid` 不注册实现。

## Decision: Legacy model-service failure semantics remain isolated

The existing model-service execution path SHALL retain its current task-state
and failure behavior, including `_set_task_state()` and `_mark_failed()`.

The annotation-kinematics pipeline SHALL use a separate checkpoint-aware task
state writer that supports:

- `execution_state`
- `attempt_count`
- `failed_stage`
- `error_code`
- structured step checkpoints

The new annotation pipeline state writer SHALL NOT replace or redefine
`_mark_failed()` as part of this Change.

For model-service tasks, newly added structured execution fields MAY remain
empty unless populated without changing existing observable behavior.

代码边界：

ModelServicePipeline
  └── 继续调用 legacy state helpers
      ├── _set_task_state()
      └── _mark_failed()

AnnotationKinematicsPipeline
  └── 使用 PipelineTaskStateWriter
      ├── claim()
      ├── start_step()
      ├── complete_step()
      ├── fail_step()
      └── complete_pipeline()

不要让两个 pipeline 共享一个越来越复杂的 `_mark_failed()`。否则为了支持
annotation pipeline 的结构化错误，很容易改变旧 model-service 的 stage、
error_message、session 状态或测试快照。

## 6. 同步与异步执行边界

dispatcher 现在只做一层分派（见 §5 的 Decision）：

async def run_analysis_task(task_id: int):
    task = load_task(task_id)
    pipeline = registry.resolve(task.pipeline_type)
    outcome = await pipeline.run(task.id, task.pipeline_version)

`ModelServicePipeline.run` 内部 `await ModelServiceClient.analyze()`；
`AnnotationKinematicsPipeline.run` 内部 `await run_in_threadpool(self._run_sync, ...)`。

新的 annotation pipeline 会执行：

SQLAlchemy
OpenCV
视频抽帧
SVG / PNG 渲染
文件存储

这些操作是同步阻塞型任务，因此放在线程池里执行。

Annotation pipeline 必须在线程内部创建和关闭自己的 `SessionLocal`，不能把路由层 SQLAlchemy Session 跨线程传递。

MVP 继续使用 `BackgroundTasks`，但数据库状态契约应保持可迁移到 Celery/Redis。现有主规格已经明确允许 MVP 使用 `BackgroundTasks`，同时要求任务状态持久化。

## 7. 输入锁定和验证

`validating_input` 阶段必须重新读取任务快照，不按 session 查“最新标注”。

校验顺序：

1. analysis_input.annotation_id 存在
2. NormalizedAnnotation 存在
3. annotation.revision == locked revision
4. annotation.session_video.session_id == task.session_id
5. session_video.view_type == side
6. annotation quality 不是 invalid
7. warning 状态已在提交时确认
8. keypoint_frames 非空
9. SessionVideo 与 VideoFile 仍存在
10. pipeline_version == side_2d_v1

不得使用：

session → 最新 NormalizedAnnotation

替代任务快照。

revision 变化：

error_code   = ANNOTATION_REVISION_DRIFT
failed_stage = validating_input
status       = failed

旧任务不能自动升级到新 revision。

## Decision: Background task must resolve the pipeline owner from the task snapshot

两个下游服务接收的是 `User` ORM 对象，而不是单纯的 user ID：

generate_review_findings(db, annotation_metric_id, current_user: User, ...)
assemble_five_page_kinematics_report(db, annotation_metric_id, current_user: User)

因此 annotation pipeline 在输入验证阶段应通过任务所属 session 的 `coach_id`
解析执行用户：

owner = db.get(User, task.session.coach_id)
if owner is None:
    raise PipelineExecutionError(
        code="TASK_OWNER_UNAVAILABLE",
        stage="validating_input",
        message="分析任务所属用户不存在",
    )

然后将这个 `owner` 传给 findings 和 assembly service。不能伪造一个只含 `id`
的对象，也不能依赖路由请求中的 `current_user`，因为后台任务运行时已脱离请求上下文。

## 8. 阶段、进度和总体状态

| stage                | status        | progress |
| -------------------- | ------------- | -------: |
| queued               | queued        |        5 |
| validating_input     | processing    |       10 |
| calculating_metrics  | processing    |       25 |
| generating_artifacts | processing    |       45 |
| running_findings     | processing    |       65 |
| saving_result        | result_saving |       78 |
| assembling_report    | result_saving |       88 |
| completed            | completed     |      100 |
| failed               | failed        |   保留最近进度 |

失败时必须先记录：

failed_stage = 当前 stage
error_code
error_message

然后才将：

stage = failed
status = failed

否则会丢失实际失败位置。

## 9. execution_state

建议结构：

{
  "schema_version": "analysis-execution.v1",
  "attempt": 2,
  "pipeline": {
    "type": "annotation_kinematics",
    "version": "side_2d_v1"
  },
  "input": {
    "annotation_id": 401,
    "annotation_revision": 3,
    "session_video_id": 201
  },
  "steps": {
    "validation": {
      "status": "completed"
    },
    "metrics": {
      "status": "completed",
      "annotation_metric_id": 701,
      "source_revision": 3
    },
    "artifacts": {
      "status": "completed",
      "artifact_set_id": 801,
      "generation_signature": "...",
      "artifact_status": "ready",
      "reused": true
    },
    "review_findings": {
      "status": "completed",
      "finding_set_id": 901,
      "generation_signature": "...",
      "reused": true
    },
    "analysis_result": {
      "status": "completed",
      "analysis_result_id": 1001
    },
    "report": {
      "status": "completed",
      "report_id": 1101,
      "generation_signature": "...",
      "assembly_status": "ready"
    }
  },
  "warnings": []
}

更新 JSON 字段时必须创建新 dict 后重新赋值，避免 SQLAlchemy 无法检测原地嵌套修改。

## 10. 指标阶段

调用：

metrics, annotation_metric_id = calculate_and_persist(
    db,
    normalized_annotation_id=annotation.id,
    persist=True,
    current_user_id=coach_id,
    calculator=CALCULATOR_SIDE_2D_KINEMATICS,
)

完成后强制验证：

metric.normalized_annotation_id == locked annotation ID
metric.source_revision == locked revision
metric.calculator == side_2d_kinematics
metric.schema_version == swim-side-kinematics.v1

相同输入重试时使用现有 upsert 记录，不新增重复 metric。

## 11. Artifacts 阶段

调用：

artifact_set, created = generate(
    db,
    annotation_metric_id,
    force=force_artifacts,
    current_user_id=coach_id,
)

`force_artifacts` 规则：

不存在当前 expected-signature set
→ force = false，正常创建

当前 set 为 ready 或 partial
→ force = false，直接复用

当前 set 为 failed 且本任务正在 retry
→ force = true，原地重新生成

以下状态允许继续：

ready
partial
failed（生成服务正常返回，但无可用资产）

`failed` 会导致最终五页报告为 partial，但不是自动伪造资产。

生成服务抛出系统异常时，任务失败并等待 retry。

## 12. Review findings 阶段

调用：

finding_set, created = generate_review_findings(
    db,
    annotation_metric_id,
    current_user,
    rule_set="side_2d_kinematics_v1",
    force=force_findings,
)

以下情况都属于有效结果：

ready + findings 非空
ready + findings 为空

“没有命中规则”和“没有生成 finding set”必须严格区分。

发现仍保持：

status = review_required

不得转换成确定性 diagnostics。

## 13. AnalysisResult 语义

`AnalysisResult` 当前要求 metrics、diagnostics、raw_result 等 JSON 字段。

Annotation pipeline 写入：

AnalysisResult(
    task_id=task.id,
    schema_version="swim-analysis.annotation-kinematics.v1",
    detections=[],
    keypoint_frames=[],
    phases=[],
    metrics=annotation_metric.metrics,
    diagnostics=[],
    quality_summary=quality_summary,
    raw_result={
        "pipeline": {
            "type": "annotation_kinematics",
            "version": "side_2d_v1",
        },
        "input": {
            "normalized_annotation_id": annotation.id,
            "annotation_revision": annotation.revision,
        },
        "products": {
            "annotation_metric_id": annotation_metric.id,
            "artifact_set_id": artifact_set.id,
            "review_finding_set_id": finding_set.id,
        },
        "review_findings": {
            "finding_set_id": finding_set.id,
            "count": len(finding_set.findings),
        },
    },
)

重试时按 `task_id` upsert，不新增第二条 AnalysisResult。

## 14. 质量聚合

## Decision: Use a dedicated side_2d_kinematics quality adapter (not a profile on the legacy aggregator)

现有 `AnalysisQualityAggregator`（`backend/app/services/metrics/quality.py`）
硬编码旧指标键 `body_angle_deg_avg`、`swolf`、`streamline_index` 等，且按
`body_position / arm_entry / catch_pull / leg_kick / efficiency` 五个模块聚合。
它既不能直接消费 `Side2DKinematicsQualityEvaluator` 产出的 issue 列表，也无法
对接新的 23 个 canonical 指标。

因此本 Change 采用专用适配器，而非在旧聚合器上加 profile：

aggregate_side_2d_kinematics_quality(
    annotation_quality,          # AnnotationQualityReport
    metric_quality,              # Side2DKinematicsQualityEvaluator 产出的 issue dict
) -> AnalysisQualitySummary

数据流：

annotation-quality.v2（模块：body_position/arm_entry/catch_pull/leg_kick/efficiency）
        +
Side2DKinematicsQualityEvaluator 的 issue 列表（按 metric + 连续帧区间聚合）
        ↓
side_2d_kinematics quality adapter
  - 把 evaluator 的 issue codes 映射为四个报告模块可用性
  - 桥接 annotation 的 5 个模块键 → 报告 4 个模块键（两者不同名，必须显式映射）
        ↓
analysis-quality.v1（模块：body_posture / upper_limb / lower_limb / head_trunk）

四个报告模块映射固定为：

body_posture
upper_limb
lower_limb
head_trunk

issue → 模块归属（示例，实现时按 evaluator 的 issue code 归类）：
- REFERENCE_BODY_LENGTH_INSUFFICIENT / TEMPORAL_CONTINUITY_LOW / FRAME_MAPPING_UNVERIFIED
  → body_posture（以及影响归一化类 upper/lower 指标时同步降级）
- HEAD_POINTS_INSUFFICIENT → head_trunk
- STROKE_CONTEXT_UNKNOWN → upper_limb / lower_limb（周期性指标降级）
- METRIC_SAMPLE_INSUFFICIENT / SINGLE_SIDE_FALLBACK / PERIODICITY_PEAK_WEAK
  → 按所影响的指标族落到对应模块

报告可用性：

指标完全不可用
→ blocked

部分指标 low_confidence / unavailable
→ degraded

核心指标正常
→ full

不要为了复用旧聚合器而把新指标伪装成旧指标键。后续若要统一更多 calculator，
再把该适配器抽象为 quality profile registry；本 Change 仅落地专用实现。

## 15. 报告装配和持久化

调用：

report_model = assemble_five_page_kinematics_report(
    db,
    annotation_metric_id,
    current_user,
)
report_data = report_model.model_dump(mode="json")

## Decision: Report content is stable per generation signature; execution trace lives outside the payload

报告内容（决定 generation_signature 的部分）必须只依赖稳定的来源输入，
不能包含随重试变化的执行信息。否则“相同签名不重复改写”与“任务引用保持正确”
会相互矛盾。

因此把追溯信息分为两类：

（1）稳定的来源追溯写入 `report_data.source_trace`（参与签名，重试不变）：

{
  "source_trace": {
    "normalized_annotation_id": 401,
    "annotation_revision": 3,
    "annotation_metric_id": 701,
    "artifact_generation_signature": "...",
    "finding_generation_signature": "...",
    "report_generation_signature": "...",
    "pipeline_type": "annotation_kinematics",
    "pipeline_version": "side_2d_v1"
  }
}

（2）随执行变化的任务信息不要写入报告内容，它们已有更合适的位置：

task_id            → ReportMetadata.task_id
analysis_result_id → AnalysisResult.raw_result
attempt / failed_stage → AnalysisTask.execution_state

即：删除原设计里 `report_data.pipeline_trace` 中的 `task_id` /
`analysis_result_id` / `attempt`，仅保留 pipeline 类型与版本作为来源描述。
这样相同 generation_signature 才真正对应相同 report_data，满足“不改写内容”
与“来源可追溯”同时成立。

ReportMetadata 更新规则：

按 session_id 查找（需先取得 session 行锁，见 §21）

存在：
  task_id = 当前 task.id
  source = annotation_kinematics
  report_data = 完整五页报告
  generated_at = now
  exported PDF → pdf_status = stale

不存在：
  创建 ReportMetadata

不使用 `merge_into_existing()`，避免旧 model-service 报告字段残留。

同一 generation signature 重试时：

report_data 内容不重复装配或重写；
report_data 之外的引用（task_id / execution_state）通过报告持久化步骤统一刷新。

## Decision: The latest successfully persisted pipeline report becomes the current session report

`ReportMetadata` remains a mutable current-report projection with one row per
session. It is not an immutable report history table.

When multiple pipeline types have produced reports for the same session, the
last pipeline that successfully persists a complete report payload SHALL become
the current report owner.

The winning pipeline SHALL be identifiable through:

- `ReportMetadata.task_id`
- `ReportMetadata.source`
- the report payload's `source_trace`
- the report payload's generation signature

The annotation pipeline SHALL replace the complete `report_data` payload rather
than merge it with an earlier model-service report.

A pipeline SHALL NOT clear or replace the existing current report before its new
report has been assembled successfully. Failure before the final persistence
step SHALL leave the previous session report intact.

同一 session 可以运行多种 pipeline
          ↓
ReportMetadata 只表达“当前报告”
          ↓
最后一次成功持久化报告者胜出

这里写成“最后一次成功持久化报告者”，而不是笼统的“最后完成任务者”。指标或
artifacts 已完成、但报告装配失败的任务，不应覆盖当前报告。

MVP 阶段不必增加 pipeline 优先级，也不必阻止旧任务重试后重新成为当前报告。
以后需要报告历史、手动选择当前报告或禁止旧任务反向覆盖时，应另建
`report_versions`，而不是继续扩张当前单行模型。

## 16. 失败策略

硬失败：

annotation 不存在
revision drift
session / video 归属不一致
非 side 机位
质量 invalid
calculator 或 schema 不受支持
指标计算异常
artifact 系统异常
findings 规则执行异常
报告 assembly 异常
数据库持久化异常

允许 partial 完成：

artifact_set.status = partial
artifact_set.status = failed 但服务正常返回
当前 findings ready 但 findings = []
部分 metric unavailable / low_confidence

最终：

task.status = completed
report.assembly_status = partial
execution_state.warnings 非空

任务完成状态和报告完整度不能混为一谈。

## 17. Retry

新增：

POST /api/v1/analysis/{task_id}/retry

## Decision: Retry is scoped to annotation_kinematics only in this Change

本 Change 新增的 retry 行为只支持 annotation_kinematics。model_service 保留
既有 actions，不因本 Change 引入“同任务重新运行”。原因：

- model_service 重跑会涉及 callback 是否重复、legacy report 是否被覆盖、
  模型服务是否幂等、result 是否 upsert 等未在本 Change 确认的行为变化；
- 本 Change 已明确“model_service 行为保持不变”，retry 也属于行为。

条件：

task.status == failed
pipeline_type == annotation_kinematics
用户拥有 task.session
不存在正在执行的同一 task

retry 行为：

status = queued
stage = queued
error_code = null
error_message = null
failed_stage 保留到 execution_state.previous_failure
attempt_count 不在 route 增加，由 runner claim 时增加
重新加入 BackgroundTasks

完成状态的 partial 报告不使用 retry API；后续重新生成 optional products 应作为独立 rebuild 能力，不在本 Change 扩张。

## 18. 并发控制

runner 开始时：

SELECT analysis_tasks
WHERE id = :task_id
FOR UPDATE

检查：

completed → no-op
processing 且已被其他 runner claim → no-op
failed 且不是 retry 调用 → no-op
queued → claim

claim 后：

attempt_count += 1
status = processing
stage = validating_input

即使 BackgroundTasks 被重复注册，上游 signature 和数据库锁也不能产生重复产物。

## 19. TrainingSession 分析状态聚合

## Decision: A session's analysis status is derived, not written unconditionally by each task

一个 session 在本 Change 下可存在多个 pipeline 任务（model_service /
annotation_kinematics / 未来 hybrid）。若每个任务完成时都无条件写
`TrainingSession.status = completed`，另一个任务失败或仍在 processing 时会出现
状态相互覆盖，与“last-successful-write 报告”语义冲突。

因此引入统一聚合函数，annotation pipeline 不直接无条件写 session.status：

def refresh_session_analysis_status(db, session_id) -> None:
    tasks = db.scalars(
        select(AnalysisTask).where(AnalysisTask.session_id == session_id)
    ).all()
    if any(t.status in (queued, processing, result_saving) for t in tasks):
        new_status = ANALYZING
    elif any(t.status == completed for t in tasks) or report_exists(session_id):
        new_status = COMPLETED
    elif tasks and all(t.status == failed for t in tasks):
        new_status = FAILED
    else:
        new_status = current_status  # 无任务则保持 uploaded/原状态

    session.status = new_status

规则汇总：

存在 queued / processing / result_saving 任务
→ analyzing

不存在运行任务，但至少有 completed 任务或有效 ReportMetadata
→ completed

不存在运行任务，也不存在 completed 任务，且任务均失败
→ failed

没有任何分析任务
→ 保持原状态（如 uploaded）

model_service 的旧 `analysis_service.py:263/313/349` 无条件写入可暂保留，
但 annotation pipeline 必须通过 `refresh_session_analysis_status` 写状态。
后续若统一所有 pipeline，再把 model_service 也切到聚合器（不在本 Change）。

## 20. 失败处理的事务约束

## Decision: Roll back the work session before recording failure

Pipeline 调用的多个 SQLAlchemy service 可能自行 flush / commit，数据库异常后
原 session 常处于 failed transaction 状态。若直接执行：

state_writer.fail_step(...)
db.commit()

会再次抛出 PendingRollbackError，导致任务停留在 processing 而非 failed。

因此失败处理顺序必须固定为：

try:
    run_step()
except Exception as exc:
    db.rollback()
    record_pipeline_failure(task_id=task.id, stage=current_stage, error=exc)
    raise

更稳的做法是让 failure recorder 使用独立 session，避免依赖已损坏的工作 session：

def record_pipeline_failure(task_id, stage, error):
    with SessionLocal() as failure_db:
        task = failure_db.get(AnalysisTask, task_id)
        writer = PipelineTaskStateWriter(failure_db, task)
        writer.fail_step(stage=stage, error_code=..., error_message=...)
        failure_db.commit()

这样即使工作 session 已损坏，任务最终也能进入稳定的 failed 状态。
checkpoint pipeline 必须写进该事务约束。

## 21. 报告持久化的 session 级串行化

## Decision: Serialize report persistence per session to prevent cross-task overwrite

§18 的 task 行锁只能防止同一 task 被重复执行，不能防止两个不同 task（如
model_service task A 与 annotation_kinematics task B）同时为同一 session 写
ReportMetadata。两者都可能 SELECT → None → INSERT，撞上 `session_id` 唯一约束；
或交叉覆盖 `report_data` / `task_id` / `source` / `pdf_status`。

因此报告持久化阶段必须先取得 session 行锁，再读取并更新 ReportMetadata：

session = db.scalar(
    select(TrainingSession)
    .where(TrainingSession.id == task.session_id)
    .with_for_update()
)

取得锁后再按 §15 规则 upsert ReportMetadata。锁住 session 行能让
“读取现有报告 → 判断 last-successful-write → 写入/覆盖 → pdf_status=stale”
整个过程原子化，比依赖 `ON CONFLICT DO UPDATE` 更能保证当前报告归属正确。

可与 §19 的 `refresh_session_analysis_status` 在同一把 session 锁内顺序执行。
