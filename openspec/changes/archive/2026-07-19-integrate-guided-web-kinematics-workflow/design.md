## Context

系统已经具备完整的后端分析能力：`annotation_kinematics` pipeline 实现了七阶段流水线（validating_input → calculating_metrics → generating_artifacts → running_findings → saving_result → assembling_report → completed），覆盖输入校验、指标计算、图表生成、复核发现、结果保存和五页报告装配。前端也已具备 `ReportView.vue` 的结构化 section 渲染与 PDF 导出能力。

但是，这些能力尚未被组织成一个面向普通用户的完整 Web 工作流。当前 `/sessions/:sessionId/upload` 仍是五机位卡片主体，且"任一机位视频上传成功"就允许提交分析，没有把"侧面视频 + 可用标注"作为硬条件。前端也没有消费流水线的真实阶段、失败步骤、错误码与重试能力；工作台 `WorkspaceView.vue:68` 只识别 `swim-analysis.v1`，会把 `annotation_kinematics` 产出误报为 schema 不兼容；标注列表在刷新后会丢失 ingest 时返回的 `parse_summary` 与完整 `quality`。

本 Change 是前端主导、附带少量后端读取契约补充的集成型 Change，不重复实现任何已有的计算/生成逻辑。

## Goals / Non-Goals

**Goals:**
- 将上传页重构为可恢复的六步侧面二维运动学引导流程。
- 页面状态全部从服务端持久化数据推导，刷新后可恢复。
- 暴露真实流水线进度（七阶段、失败步骤、错误码、actions）。
- 按错误类型区分 `retry`（原任务重跑）与 `resubmit`（用当前标注新建任务）。
- 新增同一 session 下活跃 `annotation_kinematics` 任务的并发防重。
- 报告完成后提供 HTML 与 PDF 入口，并区分报告新鲜度（current / stale）。
- 让工作台兼容 `swim-analysis.annotation-kinematics.v1`。

**Non-Goals:**
- 不新增或修改运动学指标公式。
- 不修改五类图的生成逻辑。
- 不修改复核规则或五页报告内容。
- 不新增正面、俯视、水下、半水下分析能力。
- 不实现新的任务队列系统。
- 不伪造 XML 解析百分比（使用不确定进度条）。
- 不重构 PDF 导出子系统。
- 不删除现有工作台和任务管理页。
- 不新增重解析端点（复用 `POST /annotations/{annotation_file_id}/parse`）。

## Decisions

### Decision 1：保留现有路由，替换页面语义
继续使用 `/sessions/:sessionId/upload`，不新增并行入口。`SessionUploadView.vue` 变为薄容器，核心状态与操作下沉到 `useKinematicsWorkflow()`。页面标题由"多机位视频上传"改为"侧面二维运动学分析"。

### Decision 2：工作流状态全部从服务端推导
不得把当前步骤只保存在 Vue 内存或 localStorage。刷新后根据 TrainingSession、SessionVideo(side)、AnnotationFile + NormalizedAnnotation、AnalysisTask(annotation_kinematics)、ReportMetadata / report API、PDF status 恢复。

前端状态：
```ts
type WorkflowPhase =
  | 'video_required'
  | 'annotation_required'
  | 'annotation_processing'
  | 'annotation_review'
  | 'ready_to_analyze'
  | 'analysis_running'
  | 'analysis_failed'
  | 'report_ready'
```

推导优先级：
```text
存在运行中任务       → analysis_running
最新任务失败         → analysis_failed
最新任务完成         → report_ready
标注可提交           → ready_to_analyze
标注已解析           → annotation_review
标注正在 ingest      → annotation_processing
存在侧面视频         → annotation_required
否则                 → video_required
```

### Decision 3：主流程固定为侧面机位
主页面只展示一个可操作的视频输入 `view_type = side`。正面、俯视、水下、半水下放在页面底部折叠的"后续扩展机位"区域：不显示上传按钮、显示"后续扩展"标签、若历史上已绑定视频只显示"已有素材，本次不参与分析"、不删除已有数据。

### Decision 4：主标注入口固定为 CVAT Skeleton XML
固定 `source = cvat`，`accept = .xml`，按钮文案"上传 CVAT 骨架标注"。其他历史来源标注可在"已有标注"显示，但只有满足 `status=parsed`、`quality.status != invalid`、`camera_view=side`、`normalized_annotation_id != null` 才能被选择。

### Decision 5：不伪造解析百分比
ingest 是同步 HTTP 请求，前端无法知道 parser 进度。展示"上传并解析中……"的不确定进度条，返回后再展示标注帧数量、事件数量、轨迹数量、人工标签数量、质量状态与质量问题。

### Decision 6：标注列表读取契约需要扩展
当前 ingest 响应包含 `parse_summary` 和完整 `quality`，但刷新后标注列表只返回 `quality_status`、`analysis_readiness` 和 warnings。`AnnotationFileListItem` 需扩展：
```python
normalized_annotation_id: int | None
normalized_revision: int | None
parse_summary: ParseSummary | None
quality: AnnotationQualityReport | None
analysis_readiness: AnalysisReadiness | None
kinematics_module_readiness: dict[str, str] = {}  # ready|degraded|blocked
```
`kinematics_module_readiness` 固定四键：`body_posture` / `upper_limb` / `lower_limb` / `head_trunk`。这只是标注输入阶段的预计可用状态，最终报告可用性仍以 `AnalysisResult.quality_summary` 和五页报告为准。

### Decision 7：四类模块的页面语义固定
| Key | 页面名称 | 主要内容 |
| --- | --- | --- |
| `body_posture` | 身体姿态与稳定性 | 身体轴、髋部波动、姿态稳定性 |
| `upper_limb` | 上肢运动学 | 肘角、腕部轨迹、活动范围 |
| `lower_limb` | 下肢运动学 | 膝角、踝部轨迹、打腿规律 |
| `head_trunk` | 头部与躯干控制 | 头部波动、头肩关系、头躯干同步 |

状态：`ready`（可分析）/ `degraded`（可分析但结果可能降级）/ `blocked`（当前不可分析）。分析前不得显示具体技术结论。

### Decision 8：显式选择 annotation pipeline
前端显式提交：
```json
{
  "session_id": 101,
  "normalized_annotation_id": 401,
  "acknowledge_quality_warnings": true,
  "pipeline_type": "annotation_kinematics",
  "pipeline_version": "side_2d_v1"
}
```

### Decision 9：提交后停留在当前页面
提交成功后当前页面进入步骤 5，每 2–3 秒轮询任务状态，并提供"查看任务详情"次级入口。工作台保留，但不再是主流程必经页面。

### Decision 10：任务进度使用真实流水线阶段
后端七阶段与进度百分比（见 `checkpoints.py`）：
```text
validating_input      10%
calculating_metrics   25%
generating_artifacts  45%
running_findings      65%
saving_result         78%
assembling_report     88%
completed             100%
```
前端映射（用户文案）：
| 后端阶段 | 用户文案 |
| --- | --- |
| `validating_input` | 校验视频与标注 |
| `calculating_metrics` | 计算四类运动学指标 |
| `generating_artifacts` | 生成关键帧与图表 |
| `running_findings` | 生成待复核发现 |
| `saving_result` | 保存分析结果 |
| `assembling_report` | 装配五页报告 |
| `completed` | 报告生成完成 |

不得使用前端定时器模拟阶段切换。

### Decision 11：统一任务与状态读取的流水线进度投影
当前 `get_analysis_status` 手写构造 `AnalysisStatusRead`，只传基础字段，丢弃了 `pipeline_type`、`pipeline_version`、`attempt_count`、`failed_stage`、`error_code`、`execution_state`、`actions`。`AnalysisTaskRead` 虽含 pipeline 元数据但缺 `execution_state`，且三条读取路由各自手写响应。

改为：定义 `PipelineProgressRead` 与 `PipelineStepRead`，由统一 serializer `read_analysis_task(task)` 构造，列表、详情、status 三条路由全部复用。原始 `execution_state` 仍存数据库，但前端主流程消费的是 `pipeline_progress`，数据库内部 checkpoint 结构以后扩展不会直接破坏页面。

### Decision 12：支持按 session 查询最新任务
扩展现有 `GET /analysis`：`?session_id=&pipeline_type=annotation_kinematics&limit=1`，排序固定 `updated_at DESC`，保留现有无过滤行为。

### Decision 13：失败操作由错误类型决定
错误码二分：
- **输入/版本类（→ `resubmit`）**：`INVALID_INPUT`、`ANNOTATION_NOT_FOUND`、`ANNOTATION_REVISION_DRIFT`、`SESSION_MISMATCH`、`UNSUPPORTED_VIEW`、`NO_KEYPOINT_FRAMES`。因为 `retry` 仍使用原任务锁定的 annotation revision，不适合原任务重试。
- **执行阶段类（→ `retry`）**：`METRIC_PERSIST_FAILED`、`ARTIFACT_GENERATION_FAILED`、`REVIEW_FINDINGS_GENERATION_FAILED`、`REPORT_ASSEMBLY_FAILED`、`PIPELINE_INTERNAL_ERROR`。复用现有 `POST /analysis/{task_id}/retry`。

`task_actions(task)` 当前对所有失败 annotation 任务恒返回 `["retry","details"]`，需改为按错误码分类。

### Decision 14：报告步骤复用现有报告能力
任务完成后显示"查看 HTML 报告"与"导出/下载 PDF"，复用现有 `/reports/:sessionId` 与 PDF API，不在工作流页复制 report section renderer。

### Decision 15：报告与标注 revision 的新鲜度提示
比较"当前报告所引用任务"的 annotation id / revision 与当前选中标注的 `normalized_annotation_id` / `normalized_revision`；不一致时显示"当前报告基于旧版标注 rev3；当前选择为 rev4，需要重新生成报告"。旧报告仍允许查看，但不得标记为"当前报告"。

> 注意：比较基准是当前 `ReportMetadata.task_id` 所指任务（见 Decision 20），而非独立选出的最新 completed task。

### Decision 16：工作台兼容 annotation pipeline
`WorkspaceView.vue` 不应再把 `swim-analysis.annotation-kinematics.v1` 显示为"不兼容"。annotation pipeline 工作台展示视频、任务步骤、四类指标摘要、质量摘要、报告入口；不强行使用旧 `OverlayCanvas`（其 `keypoint_frames` 当前为空，证据图位于报告 artifacts 中）。

### Decision 17：Resubmit 复用 submit 端点，revision 由后端锁定
`resubmit` 是用户面向任务的动作，而非独立 API。前端刷新当前选中的 normalized annotation，调用 `POST /analysis/submit` 仅携带当前 `normalized_annotation_id`。`AnalysisSubmit` 当前**没有** annotation revision 字段，真正的 revision 由后端在创建新任务时读取 `NormalizedAnnotation` 并写入任务快照。

- `retry` = 重跑原 AnalysisTask（沿用原任务锁定的 annotation_id + revision）；
- `resubmit` = 新建 AnalysisTask（后端读取并锁定**当前** annotation.revision）。

设计原则：**annotation ID 由前端选择，revision 由后端锁定**。不要让客户端负责 revision 一致性，这比让前端携带 revision 更安全。

后端需在 `create_analysis_task()` 中增加原子级活跃任务防重：用 `with_for_update()` 锁定 TrainingSession 行，查询同一 session 下 `pipeline_type=annotation_kinematics` 且 `status ∈ {queued, processing, result_saving}` 的任务；命中则抛出领域异常 `AnalysisTaskAlreadyActiveError(existing_task_id)`，由 submit 路由映射为 HTTP 409 `ANALYSIS_TASK_ALREADY_ACTIVE` 并附 `existing_task_id`。前端收到后不显示普通错误，而是绑定并恢复 `existing_task_id` 进度。该防护只限制 annotation_kinematics，不阻止 model_service 任务。

```python
class AnalysisTaskAlreadyActiveError(Exception):
    def __init__(self, existing_task_id: int):
        self.existing_task_id = existing_task_id
        super().__init__("当前训练记录已有二维运动学分析任务正在执行")
```

```python
# service
raise AnalysisTaskAlreadyActiveError(active_task.id)

# route
except AnalysisTaskAlreadyActiveError as exc:
    raise HTTPException(
        status_code=409,
        detail={
            "error": {
                "code": "ANALYSIS_TASK_ALREADY_ACTIVE",
                "message": str(exc),
                "existing_task_id": exc.existing_task_id,
            }
        },
    )
```

### Decision 18：Pipeline 步骤顺序与历史投影归后端契约
前端不得依赖 `execution_state.steps` 当前存在的 key 推断顺序，也不得自行维护七阶段数组。`backend/app/services/analysis_pipelines/checkpoints.py` 维护规范有序阶段定义 `ANNOTATION_KINEMATICS_STAGE_SPECS`，由统一函数 `build_pipeline_progress(task)` 投影。

`execution_state.steps` 只记录已启动的步骤（不预填 pending）。历史任务 `steps={}` 不能简单"全 pending + 当前/失败步骤"，否则已完成任务会显示"校验输入：待执行……报告生成完成：已完成"的矛盾。投影算法必须按 task 整体状态推导缺失步骤：

```text
task.status = completed
→ 所有规范步骤均 completed

task.status = processing
→ 当前 stage 之前的步骤 completed
→ 当前 stage running
→ 后续步骤 pending

task.stage 不在规范列表中（model_service 等）
→ 仅将原始 stage 作为单个 step 返回（或 steps=[]，由 D22 决定）

task.status = failed
→ failed_stage 之前的步骤 completed
→ failed_stage failed
→ 后续步骤 pending

steps 中已有真实状态（来自 checkpoint writer）
→ 优先使用真实状态与 details，不被上述规则覆盖
```

兼容旧任务，不要求迁移历史 `execution_state`。前端只负责中文展示名称，不负责决定顺序。

### Decision 19：任务与状态响应共享流水线进度
`AnalysisTaskRead` 与 `AnalysisStatusRead` 均暴露同一类型 `PipelineProgressRead`：
```python
class PipelineStepRead(BaseModel):
    key: str
    status: Literal["pending", "running", "completed", "failed"]
    progress: int
    details: dict[str, Any] = Field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None

class PipelineProgressRead(BaseModel):
    pipeline_type: str
    pipeline_version: str
    attempt_count: int
    current_stage: str
    failed_stage: str | None = None
    error_code: str | None = None
    warnings: list[str] = Field(default_factory=list)
    steps: list[PipelineStepRead] = Field(default_factory=list)
```

`pipeline_progress` 会加进所有任务响应（含 `model_service`），因此 `build_pipeline_progress()` **不能**无条件套用 annotation 七阶段——`model_service` pipeline 使用的是 `model_inference` 等不同 stage。必须定义 pipeline stage 注册表，按 `pipeline_type` 选择阶段规范：

```python
PIPELINE_STAGE_SPECS = {
    "annotation_kinematics": ANNOTATION_KINEMATICS_STAGE_SPECS,
    "model_service": MODEL_SERVICE_STAGE_SPECS,
    # hybrid 等未来扩展在此登记
}
```

`build_pipeline_progress(task)` 流程：
1. 取 `PIPELINE_STAGE_SPECS.get(task.pipeline_type)`；
2. 若命中规范（annotation_kinematics），按 D18 算法投影有序 steps；
3. 若未命中（legacy / 未知 pipeline），`steps` 仅返回当前原始 `task.stage` 作为单个 step（status 与 task.status 对齐），不虚构未定义阶段，避免 legacy 工作台显示"计算四类运动学指标"等错误步骤。

两 schema 的 `pipeline_progress` 与 `actions` 必须由同一公共投影构造，不继续各自手写。原始 `execution_state` 保留为内部持久化结构，不作为前端主契约。

### Decision 20：Report freshness 以 ReportMetadata.task_id 为权威来源
已完成但基于更旧 annotation revision 的报告，保留 `workflow_phase = report_ready`，并暴露 `report_freshness = stale`。UI 显示 stale 警告与 resubmit 动作，不引入第 9 个工作流阶段。

```ts
type ReportFreshness = 'none' | 'current' | 'stale'
```
> Report freshness is an orthogonal property and SHALL NOT introduce an additional workflow phase.

报告新鲜度的比较基准**不是**"独立选出的最新 completed task"，而是当前 `ReportMetadata` 所引用的任务。报告响应本身已返回 `task_id`，新鲜度推导必须：

```text
GET /reports/{session_id}
  → ReportData.task_id
  → 读取该 task.request_payload.analysis_input.annotation_id / annotation_revision
  → 与当前选中标注的 normalized_annotation_id / normalized_revision 比较
```

理由：报告采用 last-successful-write，最新 completed task 未必等于 `ReportMetadata.task_id` 所引用的任务。

### Decision 21：Report ready 要求报告实体真实存在
阶段推导不能仅凭"最新任务 = completed"就显示 `report_ready`。应防御异常数据：

```text
task = completed 且 当前 ReportMetadata 存在 → report_ready
task = completed 但 报告 API 返回 404      → 一致性错误
```

报告缺失时不引入第 9 个 WorkflowPhase，复用 `analysis_failed` 并产生前端合成错误 `REPORT_METADATA_MISSING`，提供刷新或重新生成动作。

### Decision 22：失败恢复策略集中在错误码注册表
`task_actions()` 不应散落一长串 `if` 判断。应在 `backend/app/services/analysis_pipelines/errors.py` 定义集中恢复策略（该模块已有 `ERROR_*` 常量与 `PipelineExecutionError` 雏形）：

```python
ERROR_RECOVERY_POLICY = {
    # 输入/版本类 → resubmit（新建任务，后端锁定当前 revision）
    "INVALID_INPUT": "resubmit",
    "ANNOTATION_NOT_FOUND": "resubmit",
    "ANNOTATION_REVISION_DRIFT": "resubmit",
    "SESSION_MISMATCH": "resubmit",
    "UNSUPPORTED_VIEW": "resubmit",
    "NO_KEYPOINT_FRAMES": "resubmit",
    # 执行阶段类 → retry（重跑原任务）
    "METRIC_PERSIST_FAILED": "retry",
    "METRIC_REVISION_MISMATCH": "retry",
    "ARTIFACT_GENERATION_FAILED": "retry",
    "REVIEW_FINDINGS_GENERATION_FAILED": "retry",
    "REPORT_ASSEMBLY_FAILED": "retry",
    "PIPELINE_INTERNAL_ERROR": "retry",
    # 非用户可恢复 → details
    "UNSUPPORTED_PIPELINE_VERSION": "details",
    "TASK_OWNER_UNAVAILABLE": "details",
}
```

`task_actions(task)` 改为查表：`resubmit` 类且为 annotation pipeline 失败 → `["resubmit", "details"]`；`retry` 类 → `["retry", "details"]`；`details` 类或未知 → `["details"]`；completed → `["workspace", "report"]`。

注意补齐真实流水线已产生的错误码：`METRIC_REVISION_MISMATCH`（→ retry）、`UNSUPPORTED_PIPELINE_VERSION`（→ details，更像部署配置不一致，不应让用户反复 resubmit）、`TASK_OWNER_UNAVAILABLE`（→ details，非用户重试可解）。

### Decision 23：Report freshness 与阶段推导解耦（见 D20/D21）
freshness 是 `report_ready` 阶段内的正交属性，由 `ReportMetadata.task_id` 推导，不与 `WorkflowPhase` 耦合。

### Decision 24：统一公共投影，而非单一 serializer
`AnalysisTaskRead` 与 `AnalysisStatusRead` 顶层字段并不完全相同（`AnalysisTaskRead.id` vs `AnalysisStatusRead.task_id`；前者有 `request_payload`，后者无）。不应让一个 `read_analysis_task(task)` 同时构造两个不同 response model。改为：

```python
def build_pipeline_progress(task) -> PipelineProgressRead: ...
def build_analysis_common_payload(task) -> dict: ...
def read_analysis_task(task) -> AnalysisTaskRead: ...
def read_analysis_status(task) -> AnalysisStatusRead: ...
```

`read_analysis_task` 与 `read_analysis_status` 都复用 `build_pipeline_progress(task)`、`task_actions(task)` 与 `build_analysis_common_payload(task)`，避免三条路由漂移，但各自返回正确的 response model。

### Decision 25：四模块预分析就绪度映射规则
`kinematics_module_readiness` 由标注质量系统的真实模块键推导（非凭空默认 ready）。质量系统模块键为 `body_position` / `arm_entry` / `catch_pull` / `leg_kick` / `efficiency`，状态序为 `ready < degraded < blocked`，采用"最差状态"合并：

```python
def _worse(a, b):
    order = {"ready": 0, "degraded": 1, "blocked": 2}
    return a if order[a] >= order[b] else b

body_posture = annotation_readiness["body_position"]
upper_limb  = _worse(annotation_readiness["arm_entry"], annotation_readiness["catch_pull"])
lower_limb  = _worse(annotation_readiness["leg_kick"],  annotation_readiness["efficiency"])
head_trunk  = <头部关键点相关 issue 推导；无判断依据时默认 degraded，不得无说明地默认 ready>
```

注意 `head_trunk` 在当前质量系统**没有**直接对应键，必须显式定义推导规则（基于头部关键点相关 issue，或明确默认 `degraded`），避免"头部与躯干控制可分析"成为 UI 假象。

## Risks / Trade-offs

- **[Risk] 前端各自维护阶段顺序导致与后端漂移** → 由 Decision 18 将顺序定义为后端契约，前端只读有序数组。
- **[Risk] 并发提交产生重复活跃任务** → Decision 17 用 `with_for_update` 行锁 + 活跃查询，领域异常映射 409 让前端恢复既有任务。
- **[Risk] `execution_state` 内部结构演进破坏前端** → Decision 19 引入 `PipelineProgressRead` 作为稳定投影，原始结构仅留数据库内部。
- **[Risk] stale 报告被误认为当前报告** → Decision 20 明确 `report_freshness` 以 `ReportMetadata.task_id` 为权威，UI 必须显式标注。
- **[Risk] 失败分类错误导致用户选错恢复动作** → Decision 22 的错误码恢复策略注册表与 `task_actions` 改造必须在后端契约测试覆盖。
- **[Risk] legacy model_service 任务被套用 annotation 七阶段** → Decision 19 的 `PIPELINE_STAGE_SPECS` 注册表按 pipeline_type 选择，未命中规范则不虚构步骤。
- **[Risk] head_trunk 就绪度成为 UI 假象** → Decision 25 强制显式推导规则，禁止无说明默认 ready。

## Migration Plan

- 后端先行：扩展 schema、新增 `PipelineProgressRead`、公共投影函数、并发防重领域异常、错误码恢复策略注册表、标注列表投影、四模块就绪度映射。
- 前端跟进：类型对齐、composable、六步组件、工作台兼容。
- 旧任务 `execution_state.steps={}` 由 `build_pipeline_progress` 按 D18 算法（依据 task.status / current stage / failed stage 与规范顺序）推导历史缺失步骤，无需数据迁移。
- 回滚：后端 schema 为向后兼容扩展（新增字段），前端可独立回滚到多机位页。

## Open Questions

- 无阻塞性未决项；D17–D25 已闭合 Change 8 的边界与状态语义。
