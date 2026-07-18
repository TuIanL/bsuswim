## Context

当前三类输入已经独立存在并持久化：

```text
AnnotationMetric(swim-side-kinematics.v1)
├── calculator = side_2d_kinematics
├── calculator_version = 1.0.0
├── source_revision
└── metrics
    ├── summary          (dict[str, MetricEnvelope]，含 CANONICAL_KEYS 全部 23 个键：body_posture 6、upper_limb 6、lower_limb 6、head_trunk 5)
    ├── time_series
    ├── ranges
    ├── representative_frames
    └── quality

KinematicArtifactSet(swim-kinematic-artifacts.v1)
├── annotation_metric_id
├── source_annotation_revision
├── source_metric_hash
├── generation_signature   (含 video checksum / style / plan / stability hash)
├── status                 (ready / partial / generating / failed)
├── manifest               (dict，含 radar semantics)
└── artifacts[]

KinematicReviewFindingSet(swim-2d-review-findings.v1)
├── annotation_metric_id
├── source_annotation_revision
├── source_metric_hash
├── generation_signature   (含 rule_set / rule_file_hash / engine / threshold_basis)
├── status                 (ready / generating / failed)
└── findings[]             (每条 status 恒为 review_required)
```

视觉资产已使用稳定 `module_key`（`body_posture` / `upper_limb` / `lower_limb` / `head_trunk` / `overview`）与 `artifact_key`（见 `constants.ARTIFACT_KEYS`）。review finding 已明确按四个 category 分类，每条保留证据指标、证据帧、置信度、限制和复核问题。

`Side2DKinematicsCalculator.CANONICAL_KEYS`（calculator.py:31-59）已定义全部 23 个指标键（body_posture 6 / upper_limb 6 / lower_limb 6 / head_trunk 5），且 `_ensure_canonical()` 保证每个 canonical key 都以 `availability="unavailable"` 的 `MetricEnvelope` 存在，不会缺 key。

findings 侧已有 `get_current_review_findings()` 按 expected signature 精确解析（不按 `created_at`）。artifacts 侧**尚无**等价读取入口。

本 Change 的作用只是把三者组织成一份五页报告，不重新解释原始骨架数据。

## Goals / Non-Goals

**Goals:**

1. 固定输出五页，不生成数量动态变化的 section；
2. 指标、图、finding 都追溯到同一 `annotation_metric_id`；
3. 不使用按 `created_at` 选择的任意"最新结果"；
4. 所有输入对应当前标注 revision 与当前生成签名；
5. 缺少非必要产物时仍可形成 partial 报告；
6. section 自带分页语义，前端无需猜测；
7. 保持 review finding 的保守语义；
8. 为 Change 7、前端渲染和 PDF 导出提供稳定 JSON。

**Non-Goals:**

- 不负责"生成"上游产物；
- 不根据原始 keypoints 重新计算任何指标；
- 不根据 finding 自动生成技术原因或训练建议；
- 不引入综合技术评分；
- 不使用雷达图作为运动员能力评分；
- 不在本 Change 改造现有 `ReportMetadata` 数据库；
- 不抽象统一的 `get_current_generated_set()`，artifacts 与 findings 的签名公式保持独立；
- 不在报告层重写或硬编码雷达图免责声明。

## Decisions

### Decision 1：新增专用 assembler，不覆盖旧 builder

保留：

```python
build_report_data(...)
build_swim_report_data(...)
```

新增：

```python
build_five_page_kinematics_report(
    context: FivePageReportAssemblyContext,
) -> FivePageKinematicsReport
```

以及数据库输入服务：

```python
assemble_five_page_kinematics_report(
    db: Session,
    annotation_metric_id: int,
    current_user: User,
) -> FivePageKinematicsReport
```

旧 builder 当前绑定 `AnalysisResult` + `swim-side-metrics.v1` + legacy diagnostics + 旧 section key；新报告绑定 `AnnotationMetric` + `swim-side-kinematics.v1` + `KinematicArtifactSet` + `KinematicReviewFindingSet`。不应在一个函数里堆叠大量 schema 判断。

### Decision 2：报告按 AnnotationMetric 装配

唯一权威入口为 `annotation_metric_id`。解析链路：

```text
AnnotationMetric
  → NormalizedAnnotation
  → SessionVideo → VideoFile → TrainingSession → Athlete

AnnotationMetric
  → current KinematicArtifactSet
  → current KinematicReviewFindingSet
```

所有数据都围绕同一个事实指标快照组织。

### Decision 3：指标必须 current，其他输入可降级

必要输入：

```text
AnnotationMetric:
  calculator = side_2d_kinematics
  schema_version = swim-side-kinematics.v1
  source_revision = NormalizedAnnotation.revision
```

不满足时：

```text
404 metric_unavailable
409 metric_revision_stale
422 unsupported_metric_schema
422 invalid_metric_payload
```

非必要输入（`KinematicArtifactSet` / `KinematicReviewFindingSet`）缺失时不阻止装配，但 `assembly_status = partial` 且 `warnings` 追加 `artifacts_not_generated` / `review_findings_not_generated`。已存在但 signature 不匹配的旧产物不得被使用。

**D12（本 Change 新增）**：artifact 与 finding 分别通过自己的 expected signature resolver 解析。

artifact 的 `generation_signature` 包含 `source_video_checksum`、`generator_version`、`artifact_plan_version`、`style_profile`、`style_profile_hash`、`stability_index_config_hash`；finding 的 `generation_signature` 包含 `rule_set`、`rule_file_hash`、`engine_version`、`threshold_basis`。二者字段不同、公式不同，不能合并为一个通用 resolver，也不能让报告层自行拼接签名。

新增 artifact 模块内部的 resolver。鉴权与解析职责分离：assembly service 先统一完成一次 ownership 校验（见 Decision 2），resolver 本身只负责按 expected signature 精确解析，不做权限检查，避免一次装配里重复三遍 ownership 查询。

```python
# kinematic_artifacts/resolver.py
def compute_expected_artifact_signature(
    metric: AnnotationMetric,
    annotation: NormalizedAnnotation,
    video_file: VideoFile | None,
) -> str:
    ...

def resolve_current_artifact_set(
    db: Session,
    metric: AnnotationMetric,
    annotation: NormalizedAnnotation,
    video_file: VideoFile | None,
) -> ArtifactResolutionResult:
    """内部纯 resolver，不负责鉴权；返回结构化的解析结果。"""
    ...

class ArtifactResolutionResult(BaseModel):
    artifact_set: KinematicArtifactSet | None
    resolution_status: Literal[
        "current_ready",
        "current_partial",
        "current_generating",
        "current_failed",
        "not_generated",
    ]
    warning_code: str | None = None
```

`resolve_current_artifact_set()` 按 expected artifact signature 精确查询 `ArtifactSet`，据此映射状态：

```text
current_ready:     匹配到 status=ready            → 返回，可用于装配
current_partial:   匹配到 status=partial          → 返回，装配 assembly_status=partial
current_generating:匹配到 status=generating       → 不作为可消费资产，warning=artifacts_generating，报告 partial
current_failed:    匹配到 status=failed           → 不投影 assets，warning=artifacts_generation_failed，报告 partial
not_generated:     无当前 signature 匹配          → artifact_set=None，warning=artifacts_not_generated，报告 partial
```

`VideoFile` 缺失（无原视频）时仍可计算 expected signature（checksum 为 None），但关键帧/轨迹图会因此 skipped——这属于资产降级，由资产投影层转成 `quality_notes`，不阻断装配。

报告装配 service 调用顺序：

```python
metric = resolve_owned_annotation_metric(db, annotation_metric_id, current_user)  # 一次 ownership
ann = db.get(NormalizedAnnotation, metric.normalized_annotation_id)
artifact_result = resolve_current_artifact_set(db, metric, ann, video_file)
finding_set = resolve_current_review_finding_set(db, metric, ann)  # 内部同样走 ownership 已校验的 metric
```

职责分离：`signature.py` 提供 `canonical_json()` / `metric_hash()` / `generation_signature()` 等底层工具；`resolver.py` 负责校验 metric、校验 revision、解析 video checksum、计算 expected artifact signature、精确查询 `ArtifactSet`。报告层只调用 resolver，不感知 style profile、雷达配置和视频 checksum。findings 继续复用已有 `get_current_review_findings(...)`，其内部已做 ownership 校验（`session.coach_id == current_user.id`）。

两者**只能共享**底层稳定序列化与 SHA-256 工具，不能共享最终 signature 公式。

### Decision 4：固定五页就是固定五个 section

严格生成：

```text
1. analysis_overview
2. body_posture_control
3. upper_limb_kinematics
4. lower_limb_kinematics
5. review_and_retest
```

即使某页无可用指标也必须保留该页，`status = unavailable`，`metrics` / `assets` / `findings` 为空数组，`quality_notes` 解释原因。页面序号永远稳定。

**D13（本 Change 新增）**：section 的 `module_key` 是页面聚合键，`source_module_keys` 是事实源模块键；二者分层。

```python
class FivePageReportSection(BaseModel):
    page_number: Literal[1, 2, 3, 4, 5]
    page_type: PageType
    module_key: str                       # 报告页面聚合模块
    source_module_keys: list[str]        # 该页面消费的事实源模块
    assets: list[ReportAsset]
    metrics: list[ReportMetric]
    findings: list[ReportFinding]
    quality_notes: list[ReportQualityNote]
    content: dict = {}
```

```python
PAGE_PLAN = {
    1: {"page_type": "analysis_overview",     "module_key": "overview",
        "source_module_keys": []},
    2: {"page_type": "body_posture_control",  "module_key": "body_posture_head_trunk",
        "source_module_keys": ["body_posture", "head_trunk"]},
    3: {"page_type": "upper_limb_kinematics", "module_key": "upper_limb",
        "source_module_keys": ["upper_limb"]},
    4: {"page_type": "lower_limb_kinematics", "module_key": "lower_limb",
        "source_module_keys": ["lower_limb"]},
    5: {"page_type": "review_and_retest",     "module_key": "review_summary",
        "source_module_keys": ["body_posture", "head_trunk", "upper_limb", "lower_limb"]},
}
```

其中 `asset.module_key` 保留 artifact 原始 `module_key`（`body_posture` / `head_trunk` …），`metric.category` / `finding.category` 保留源分析模块。section 的 `module_key` 只用于标识报告页面模块，不得解释为 artifact `module_key` 或旧 `side_technical` section key。

两套 profile 互不兼容，是并存的两个独立报告 profile：

```text
side_technical               → body_position / arm_entry / catch_pull / leg_kick / efficiency
side_2d_kinematics_5page_v1 → overview / body_posture_head_trunk / upper_limb / lower_limb / review_summary
```

### Decision 5：展示型指标与单一索引

不能直接把 `MetricEnvelope` 字典扔给前端，需增加轻量展示投影 `ReportMetric`（含 `key` / `label` / `category` / `value` / `display_value` / `unit` / `availability` / `confidence` / `sample_count` / `reference_basis` / `provenance` / `details`）。

**D14（本 Change 新增，修订）**：`all_report_metrics` 只负责 23 个运动学指标（`summary` 投影）；第 1 页的输入与覆盖统计通过独立的 `overview_stats` 构建，二者数据流分离。

```text
summary
  → project_metric_envelopes()
  → all_report_metrics: dict[str, ReportMetric]   (仅 23 个 canonical 键)
        ├── Page 2 指标
        ├── Page 3 指标
        ├── Page 4 指标
        ├── Page 5 客观指标摘要
        └── Page 5 retest_metrics

NormalizedAnnotation + metric.quality + all_report_metrics
  → build_overview_stats()
  → overview_stats: list[ReportOverviewStat]       (Page 1)
```

第 1 页要求的有效帧数、关节点完整率、视频帧数、标注来源等**不属于** 23 个 `CANONICAL_KEYS`，也不进入 `KINEMATICS_REPORT_METRICS` 注册表（否则违反契约测试 `set(KINEMATICS_REPORT_METRICS) <= set(CANONICAL_KEYS)`）。`overview_stats` 用独立模型：

```python
class ReportOverviewStat(BaseModel):
    key: str
    label: str
    value: int | float | str | None
    display_value: str | None = None
    unit: str | None = None
    source: Literal["normalized_annotation", "metric_quality", "report_assembly"]
    provenance: dict = Field(default_factory=dict)

class ReportOverviewStatSource(StrEnum):
    NORMALIZED_ANNOTATION = "normalized_annotation"
    METRIC_QUALITY = "metric_quality"
    REPORT_ASSEMBLY = "report_assembly"
```

第 1 页可用指标比例 / 低置信度指标数量 / 可用模块数量可读取 `all_report_metrics` 聚合；有效帧数（`effective_frame_count`）与关节点完整率从标准化标注或其质量快照读取。关节点完整率口径必须与 frame resolver 一致，报告层不得另造：

```text
joint_completeness_ratio = 可用关节点样本数 ÷ (有效标注帧数 × 17)

其中"可用"的判定（visible / occluded / estimated 哪些计入）
必须与 frame resolver 的可见性语义一致；
优先复用已有或新增的 annotation coverage helper，而非报告层遍历原始 JSON。
```

这样复测值、单位、显示精度、置信度和 reference basis 与第 2—4 页完全一致，不会发生两套 formatter；同时 `KINEMATICS_REPORT_METRICS` 注册表保持纯净。

指标键清单已与 `CANONICAL_KEYS` 对齐（全部 23 个键覆盖）；`_ensure_canonical()` 保证缺算的指标以 `unavailable` 包络存在。仍增加静态契约测试防止未来漂移（见 tasks 4.x）。

报告层配置：

```python
KINEMATICS_REPORT_METRICS = { "<key>": {"label": ..., "order": ..., "decimals": ...}, ... }
PAGE_METRIC_KEYS = { "<page_type>": ["<key>", ...], ... }
```

原则：不修改指标原值；不做单位推断；不把 `screen_horizontal` 写成"与水面夹角"；`low_confidence` 指标可展示但必须产生质量提示；`unavailable` 指标不进入普通指标卡但记入页内缺失列表；`confidence` 与 `reference_basis` 必须保留。

### Decision 6：状态语义分三层并改名

**D15（本 Change 新增）**：区分 source status、section status、report assembly status，避免同名混淆。

| 字段 | 命名空间 | 含义 |
|---|---|---|
| `MetricEnvelope.availability` | 单项指标质量 | available / low_confidence / unavailable |
| `section.status` | 单页装配完整度 | ready / partial / unavailable |
| `report.assembly_status` | 五页报告装配完整度 | ready / partial |
| `artifact_set.status` | 视觉资产生成结果 | ready / partial / generating / failed |
| `finding_set.status` | 规则发现生成结果 | ready / generating / failed |
| `revision_status` | 输入修订新鲜度 | current / stale / unknown |

报告顶层状态字段命名为 `assembly_status: Literal["ready", "partial"]`。为兼容现有报告结构可同时输出 `status` 作为别名，但后续代码统一读取 `assembly_status`。报告层**不得**把 `artifact_set.status = partial` 重解释为 `section.status` 或改写其含义——只能基于上游事实推导自己的状态并保留上游原始状态。

顶层 `assembly_status` 推导：

```text
ready:
  page 2/3/4 均非 unavailable
  artifact set 当前有效
  finding set 当前有效
  无 blocking warning

partial:
  任一技术页 unavailable
  或 artifact set 缺失 / partial
  或 finding set 未生成
  或存在 degraded quality
```

"规则已运行但 findings 为空"是合法 ready 状态（finding set status = ready，空列表），不等同于 findings 未生成。

### Decision 7：雷达图语义只透传

**D16（本 Change 新增）**：雷达图语义（含免责声明）只能从 `KinematicArtifactSet.manifest` 透传，报告层不得硬编码。

```python
radar_semantics = (
    artifact_set.manifest.get("radar")
    if artifact_set and isinstance(artifact_set.manifest, dict)
    else None
)
```

写入第 5 页 `content.radar_semantics`（保留 `semantics` / `overall_score=None` / `disclaimer` / `index_method_version` / `config_hash`）。若 radar artifact 缺失，`radar_semantics` 仍可保留、`asset` 不进入第 5 页 `assets`、`quality_notes` 记录 radar asset unavailable；若整个 artifact set 缺失，`radar_semantics = null`，不在报告层构造默认免责声明。

## 五页装配规则

### 第 1 页：数据与分析概况

`page_type = analysis_overview`，`module_key = overview`，`source_module_keys = []`。`content` 含 athlete / session / video / annotation / quality / available_modules / analysis_boundaries。指标仅放数据质量与覆盖情况（有效帧数、关节点完整率、可用指标比例、低置信度指标数量、可用模块数量）。`assets = []`，`findings = []`。

### 第 2 页：身体姿态与头躯干控制

`module_key = body_posture_head_trunk`，`source_module_keys = [body_posture, head_trunk]`。指标含 torso/body axis、hip/shoulder/head vertical range、body_angle_std、posture_stability_cv、head 相关指标。资产顺序：body_axis_min → body_axis_max → angle_timeseries → hip_trajectory → head_motion_spike → overview range_comparison。findings 取 `category ∈ {body_posture, head_trunk}`。

### 第 3 页：上肢运动学

`module_key = upper_limb`，`source_module_keys = [upper_limb]`。最大屈肘从 `left_elbow_min` / `right_elbow_min` 中选 `metadata.value` 更小者；最大伸展从 `left_elbow_max` / `right_elbow_max` 中选更大者（报告层只筛选，不重算）。资产顺序：selected flexion → selected extension → elbow_angle_timeseries → joint_trajectories → arm_extension_max。findings 取 `category = upper_limb`。

### 第 4 页：下肢运动学

`module_key = lower_limb`，`source_module_keys = [lower_limb]`。最大屈膝/伸膝同理跨侧选择。资产顺序：selected flexion → selected extension → knee_angle_timeseries → joint_trajectories。findings 取 `category = lower_limb`。

### 第 5 页：关键发现与复核建议

`module_key = review_summary`，`source_module_keys = [body_posture, head_trunk, upper_limb, lower_limb]`。本页**不能**变成训练处方页。assets 含 `overview.chart.range_comparison` 与 `overview.chart.stability_radar`，并透传 radar semantics。优先复核问题按 `(priority, -priority_score, ATTENTION_RANK[attention_level], -confidence, code)` 排序，首页摘要最多 3 条、第 5 页最多 8 条。`content` 含：

- `objective_metric_summary`：从 `all_report_metrics` 派生
- `priority_review_findings`：完整排序结果
- `evidence_frame_index`：对 findings 的 `evidence_frames` 按 `(source_video_frame, annotation_frame, finding priority)` 去重排序
- `limitations`：合并 finding.limitations + metric quality + artifact warnings/skip reasons + frame mapping status + reference basis + missing module metrics，去重
- `next_capture_suggestions`：仅数据采集层建议（如 `frame_mapping_unverified` → 提供帧映射），**不得**输出力量/推进力/打腿/乳酸类训练处方
- `retest_metrics`：见下方

**D14 续 / 复测指标与 finding 派生键映射（修订）**：复测指标统一从 `all_report_metrics` 取数值，但 `finding.evidence_metrics[].key` **不保证是 canonical metric key**——Change 5 adapter 会生成派生逻辑键（如 `hip_vertical_range_ratio`、`elbow_rom_asymmetry_deg`、`minimum_knee_p05_deg`）。因此不能直接 `all_report_metrics[evidence.key]`，必须先解析：

```python
def resolve_retest_source_metric_keys(
    evidence: FindingEvidenceMetric,
) -> list[tuple[str, str | None]]:
    """返回 (canonical_metric_key, statistic) 列表。

    evidence.key 可能解析到：
      summary.hip_vertical_range_px        → ("hip_vertical_range_px", None)
      summary.elbow_rom_deg                → ("elbow_rom_deg", None)
      ranges.left_knee_angle_deg.p05       → ("left_knee_angle_deg", "p05")
      reference_body_length.value_px       → 不进入 canonical ReportMetric；
                                            作为 retest dependency / supporting input 记录
    """
    ...

class RetestMetric(BaseModel):
    metric_key: str
    label: str
    current_value: Any = None
    display_value: str | None = None
    unit: str | None = None
    reference_basis: str | None = None

    trigger_metric_key: str | None = None   # 触发该复测项的 finding 派生键
    derivation: str | None = None           # 如 "hip_vertical_range_px / reference_body_length.value_px"
    statistic: str | None = None            # p05 / min / max ...
    reason: str
```

解析规则以 `evidence.source_metric_keys` + `evidence.derivation` 为准，回退到 `evidence.key`；命中 canonical 键时记入 `all_report_metrics` 数值，未命中的 reference_body_length 等作为 supporting input 记录但不伪造 canonical 值。既保持数值来自 `all_report_metrics`，又不丢失 finding 使用归一化派生指标这一事实。

选择顺序固定：

```text
1. finding.evidence_metrics 经解析命中 canonical 键的指标
2. availability = low_confidence 的页面核心指标
3. 已展示且属于 RETEST_CORE_KEYS 的指标
```

`RETEST_CORE_KEYS` 在 Change 6 固定最小稳定集合（不留到 Change 7，避免同 profile 跨 Change 改变语义）：

```python
RETEST_CORE_KEYS = [
    "body_axis_angle_deg", "body_angle_std_deg", "hip_vertical_range_px",
    "elbow_rom_deg", "knee_rom_deg", "ankle_vertical_range_px",
    "head_vertical_range_px", "kick_periodicity",
]
# 不默认纳入：wrist_velocity_px_per_frame / left_right_kick_timing / head_body_synchrony
# （对 frame mapping、连续性和片段长度更敏感，仅在 finding 引用或 low_confidence 时进入）
```

去重键 `metric_key`，排序 `(finding priority, low_confidence first, page number, registry order, metric_key)`。仅记录下次应重复测量什么，不设未经验证的"目标值"。

## ReportAsset / ReportFinding 投影

`ReportAsset` 扩展投影结果，保留 `artifact_type` / `module_key` / `metric_keys` / `annotation_frame` / `source_video_frame` / `width` / `height` / `mime_type` / `checksum_sha256` / `source_annotation_revision` / `generator_version` / `metadata`。`skipped` / `failed` 资产不进入 `assets`，转成 `quality_notes`。

`ReportFinding` 保留 `code` / `rule_id` / `title` / `category` / `status="review_required"` / `attention_level` / `priority` / `priority_score` / `evidence_metrics` / `evidence_frames` / `confidence` / `confidence_level` / `limitations` / `review_question` / `threshold_basis`。页面 2—4 按 category 过滤；页面 5 保留完整排序结果。不得映射到 diagnostics / recommendations / training_suggestions。

## 生成签名与 source trace

报告 `generation_signature` 至少包含：`annotation_metric_id`、`source_revision`、metric payload hash、`artifact_set.generation_signature` 或 `"missing"`、`artifact_set.manifest_sha256`（已持久化）、`finding_set.generation_signature` 或 `"missing"`、`finding_payload_hash`（装配时稳定计算）、`report_profile`、`report_profile_version`、`assembler_version`、`report_config_hash`。

其中：

```python
finding_payload_hash = stable_hash({
    "findings": finding_set.findings,
    "summary": finding_set.summary,
    "warnings": finding_set.warnings,
    "skipped_rules": finding_set.skipped_rules,
})

report_config_hash = stable_hash({
    "KINEMATICS_REPORT_METRICS": ...,
    "PAGE_METRIC_KEYS": ...,
    "PAGE_PLAN": ...,
    "PAGE_READINESS_POLICY": ...,
    "RETEST_CORE_KEYS": ...,
    "next_capture_suggestion_map": ...,
    "finding_display_limits": ...,
})
```

加入 `manifest_sha256` 与 `finding_payload_hash` 的原因是：上游 set 可被 `force=True` 原地复用同一 generation_signature 并重新生成 artifact rows / manifest，仅依赖上游 signature 不足以代表"本次装配实际读取到的内容"。`report_config_hash` 覆盖所有会改变报告输出的配置，比仅含 presentation config + page plan 更完整。

`source_trace` 原样保留上游状态：

```json
{
  "annotation_metric": {"id": ..., "schema_version": ..., "calculator": ..., "source_revision": ..., "payload_hash": ..., "revision_status": "current"},
  "artifact_set": {"id": ..., "generation_signature": ..., "manifest_sha256": ..., "status": "partial", "resolution_status": "current_partial"},
  "review_finding_set": {"id": ..., "rule_set": ..., "generation_signature": ..., "status": "ready"},
  "assembler": {"name": "five_page_kinematics_report", "version": "1.0.0", "profile": "side_2d_kinematics_5page_v1"}
}
```

## API 设计

```http
POST /api/v1/annotation-metrics/{annotation_metric_id}/reports/five-page/assemble
```

认证用户只能读取自己训练记录下的 metric；不自动运行指标/图/findings 生成；不写入 `ReportMetadata`；返回完整五页 JSON。Change 7 后续直接调用相同 service 并持久化。

错误码：`404 metric_unavailable` / `404 annotation_unavailable` / `409 metric_revision_stale` / `422 unsupported_metric_schema` / `422 invalid_metric_payload` / `500 report_assembly_failed`。缺少 artifact 或 findings 不返回错误，而是 partial。

## Risks / Trade-offs

- **[Risk] artifact current resolver 是新增工作量，且与 findings resolver 不共享公式** → Mitigation：仅抽取底层 `canonical_json` / `metric_hash` 工具，新增独立 `resolver.py`，加回归测试证明报告层各自通过自有签名解析两个上游产物。
- **[Risk] 指标键清单未来与 calculator 漂移** → Mitigation：增加 registry 契约测试 `configured ⊆ CANONICAL_KEYS` 与 `page_keys ⊆ KINEMATICS_REPORT_METRICS`。
- **[Risk] 三层 fixture 不存在完整可复用版本** → Mitigation：Change 6 新增 `build_persisted_kinematics_report_fixture()`，基于 `build_golden_annotation()` + 真实 calculator/artifact/finding 服务组合，而非手写 JSON（见 D17）。
- **[Risk] `status` 与上游 `partial` 同名混淆** → Mitigation：顶层改用 `assembly_status`，状态命名空间文档化（Decision 6）。
- **[Risk] 报告层误改写 radar 免责声明** → Mitigation：强制从 manifest 透传，禁止字面量硬编码（Decision 7）。

## D17：完整持久化三层 fixture（本 Change 新增）

仓库已有 `build_golden_annotation()`（50 帧、verified frame mapping）与 artifact generation 测试底座，但尚无可直接复用的完整三层 fixture。Change 6 必须新增：

```python
@dataclass
class KinematicsReportFixture:
    user, athlete, session, video_file, session_video,
    annotation, metric, artifact_set, finding_set

def build_persisted_kinematics_report_fixture(
    db, *, with_video=True, with_artifacts=True,
    with_findings=True, artifact_status=None, no_matching_findings=False,
) -> KinematicsReportFixture:
    ...
```

内部尽量走真实服务：`build_golden_annotation()` → 持久化 `NormalizedAnnotation` → `Side2DKinematicsCalculator.calculate()` → 持久化 `AnnotationMetric` → `generate()` artifacts → `generate_review_findings()`。支持变体：complete / missing artifacts / missing findings / empty ready findings / partial artifacts / stale metric / stale artifact only / stale finding only / low-confidence module / unavailable module。

## D18：页面完整度策略（PAGE_READINESS_POLICY）

`section.status` 不能只靠实现者直觉，必须显式策略：

```python
PAGE_READINESS_POLICY = {
    "analysis_overview": {
        "required_metric_keys": [],
        "preferred_asset_groups": [],
    },
    "body_posture_control": {
        "required_metric_groups": [["body_axis_angle_deg", "torso_axis_angle_deg"]],
        "preferred_asset_groups": [["body_posture.chart.angle_timeseries"]],
    },
    "upper_limb_kinematics": {
        "required_metric_groups": [["left_elbow_angle_deg", "right_elbow_angle_deg"]],
        "preferred_asset_groups": [["upper_limb.chart.elbow_angle_timeseries"]],
    },
    "lower_limb_kinematics": {
        "required_metric_groups": [["left_knee_angle_deg", "right_knee_angle_deg"]],
        "preferred_asset_groups": [["lower_limb.chart.knee_angle_timeseries"]],
    },
}
```

语义：

```text
unavailable:
  没有任何 required metric group 可用（整组 key 均 unavailable）

partial:
  required metric 可用，但存在低置信度、
  缺少 preferred assets、或对应上游 set 为 partial

ready:
  required metric 可用且非低置信度、
  preferred assets 可用、对应上游 set ready
```

第 5 页单独判断：`finding set ready`（即使 `findings=[]`）→ finding 输入完整；`finding set missing/generating/failed` → page 5 partial。

## Open Questions（已拍板）

- **RETEST_CORE_KEYS**：在 Change 6 固定最小稳定集合（见 D14 续），不留到 Change 7。
- **golden snapshot 归一化**：分两层测试。
  - 第一层验证真实字段：`generation_signature` 非空且长度 64；`source_trace` 各 ID 与 fixture 对象一致；section 内 asset URL 指向对应 artifact。
  - 第二层再做 snapshot normalization：
    ```python
    NORMALIZED_FIELDS = {
        "generated_at": "<TIMESTAMP>",
        "generation_signature": "<SIGNATURE>",
        "source_trace.annotation_metric.id": "<METRIC_ID>",
        "source_trace.artifact_set.id": "<ARTIFACT_SET_ID>",
        "source_trace.review_finding_set.id": "<FINDING_SET_ID>",
    }
    ```
    URL 不整项删除，只归一化动态前缀：`/uploads/kinematic-artifacts/123/r3/abcdef/xxx.svg` → `/uploads/kinematic-artifacts/<METRIC_ID>/r<REV>/<SIG>/xxx.svg`，以保留对 artifact filename 与页面映射的检查。
