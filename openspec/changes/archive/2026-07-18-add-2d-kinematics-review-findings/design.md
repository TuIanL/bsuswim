# Design: add-2d-kinematics-review-findings

## 1. 目标数据流

```text
AnnotationMetric
calculator = side_2d_kinematics
schema = swim-side-kinematics.v1
        │
        ▼
Side2DKinematicsReviewAdapter
        │
        ├── 展平 MetricEnvelope
        ├── 生成归一化派生指标
        ├── 提取 ranges / time_series
        └── 保留 availability / confidence / provenance
        │
        ▼
KinematicReviewFindingsEngine
        │
        ├── 加载 side_2d_kinematics_v1
        ├── 检查 required_metrics
        ├── 评估结构化条件
        ├── 解析注意级别
        ├── 生成 evidence_metrics
        ├── 选择 evidence_frames
        ├── 计算 confidence
        └── 填充 limitations / review_question
        │
        ▼
KinematicReviewFindingSet
        │
        ├── findings[]
        ├── summary
        ├── skipped_rules
        ├── warnings
        └── generation_signature
```

当前 metrics API 已经提供按 `annotation_metric_id` 读取记录的入口，而且代码注释明确说明该入口供 Change 5 直接引用，因此新链路应从 `AnnotationMetric` 开始，而不是先构造一个虚假的 `AnalysisResult`。

## 2. 核心决策

### Decision 1：新增 ReviewFinding，不扩充旧 DiagnosticItem

旧 `DiagnosticItem` 继续表达正式诊断，新对象表达待复核发现：

```python
class FindingEvidenceMetric(BaseModel):
    key: str
    source_metric_keys: list[str]
    derivation: str | None = None
    label: str
    value: float | int | str | None
    unit: str | None
    availability: Literal[
        "available",
        "low_confidence",
        "unavailable",
    ]
    confidence: float

    comparison: str | None = None
    threshold: float | list[float] | None = None
    reference_basis: str | None = None


class FindingEvidenceFrame(BaseModel):
    metric_key: str
    annotation_frame: int
    source_video_frame: int | None = None
    time_sec: float | None = None

    role: Literal[
        "minimum",
        "maximum",
        "peak",
        "trough",
        "spike",
        "max_deviation",
        "representative",
        "context",
    ]

    value: float | None = None
    extractable: bool = False
    mapping_status: str = "unknown"


class KinematicReviewFinding(BaseModel):
    code: str
    rule_id: str

    title: str
    category: Literal[
        "body_posture",
        "upper_limb",
        "lower_limb",
        "head_trunk",
    ]

    status: Literal["review_required"] = "review_required"
    attention_level: Literal["low", "medium", "high"]
    priority: int
    priority_score: float

    evidence_metrics: list[FindingEvidenceMetric]
    evidence_frames: list[FindingEvidenceFrame]

    confidence: float
    confidence_level: Literal["low", "medium", "high"]

    limitations: list[str]
    review_question: str

    threshold_basis: str = "project_heuristic_v1"
```

这里不设置 `reason` 和 `training_suggestion`，避免二维运动学结果越权推断身体能力或直接开训练处方。

### Decision 1b：Adapter 返回带元数据的包装对象，不只用扁平上下文

`DiagnosticMetricsContext.metrics` 本质是 `dict[str, Any]`，若把派生指标（如
`hip_vertical_range_ratio = hip_vertical_range_px / reference_body_length`）展平为单个数字，
原指标的 `confidence` / `availability` / `source_metric_keys` / `provenance` 就会丢失，
后续 engine 无法判断该派生指标是否由低置信度参考体长算出。

因此 Adapter SHALL 返回包装对象：

```python
class ReviewMetricMeta(BaseModel):
    key: str
    source_metric_keys: list[str]
    value: float | int | str | None
    unit: str | None
    availability: Literal["available", "low_confidence", "unavailable"]
    confidence: float
    reference_basis: str | None = None
    derivation: str | None = None


class ReviewAdapterResult(BaseModel):
    evaluation_context: DiagnosticMetricsContext
    metric_meta: dict[str, ReviewMetricMeta]
    warnings: list[str] = []
```

使用分工：

```text
evaluation_context.metrics        → evaluate_trigger / evaluate_severity_branch
metric_meta                      → evidence_metrics / confidence / limitations / provenance
```

派生指标的可信度传播规则（强制）：

```text
availability = 所有来源指标中最差的 availability
confidence   = 所有来源指标 confidence 的最小值
```

例：

```text
hip_vertical_range_ratio
availability = worst(hip_vertical_range_px.availability, reference_body_length.availability)
confidence   = min(hip_vertical_range_px.confidence, reference_body_length.confidence)
```

`evaluation_context.metrics` 仅承载标量值供评估器使用；`metric_meta` 承载溯源与质量信息供
evidence / confidence / limitations 构建。两者键名一致。

### Decision 2：新增独立 finding set 持久化

不把 findings 写进 `annotation_metrics.metrics`，也不提前写入 `analysis_results`。

```python
class KinematicReviewFindingSet(Base):
    __tablename__ = "kinematic_review_finding_sets"

    id
    annotation_metric_id
    normalized_annotation_id
    session_video_id

    schema_version
    rule_set
    rule_version
    engine_version
    threshold_basis

    source_annotation_revision
    source_metric_schema_version
    source_metric_calculator
    source_metric_calculator_version
    source_metric_hash

    generation_signature
    status

    findings
    summary
    skipped_rules
    warnings

    created_by
    created_at
    updated_at
```

`status` 枚举固定为：

```text
generating
ready
failed
```

force 重新生成时流转为 `ready → generating → ready`。失败处理采用"先内存计算、
成功后一次性覆盖"：

```text
旧 ready 数据继续保留
→ 新结果全部计算成功
→ 单事务覆盖 findings 与 metadata
```

SHALL NOT 先清空已有 findings 再计算，否则失败会破坏原有效结果。失败时置 `failed`
并记录 error，旧 `ready` 数据保留可供 GET 回退。

唯一约束：

```text
UNIQUE(annotation_metric_id, generation_signature)
```

其版本追踪方式与当前 artifact set 的 source revision、metric hash 和 generation signature 思路保持一致。

### Decision 3：规则不得直接读取 MetricEnvelope

新增 adapter 将复杂结构转换为稳定标量上下文。

```text
原始来源                                      规则逻辑键
─────────────────────────────────────────────────────────────────
summary.body_angle_std_deg.value              body_angle_std_deg
summary.posture_stability_cv.value             posture_stability_cv

summary.hip_vertical_range_px.value
÷ reference_body_length.value_px               hip_vertical_range_ratio

summary.elbow_rom_deg.details.left             elbow_rom_left_deg
summary.elbow_rom_deg.details.right            elbow_rom_right_deg
summary.elbow_rom_deg.details.combined         elbow_rom_combined_deg
abs(left - right)                              elbow_rom_asymmetry_deg
abs(left-right) / max(left,right)              elbow_rom_asymmetry_ratio

ranges.left_knee_angle_deg.p05                 left_knee_p05_deg
ranges.right_knee_angle_deg.p05                right_knee_p05_deg
min(left, right)                               minimum_knee_p05_deg

summary.kick_periodicity.value.score           kick_periodicity_score
summary.kick_periodicity.value.period_frames   kick_period_frames

summary.kick_periodicity.details.reason         （用于派生下列二键）
sample_count                                    sample_count

# 由 Adapter 派生的周期可评估标志（关键：区分"样本不足"与"无稳定周期峰"）
kick_periodicity_evaluable                      1=样本充分可评估 / 0=样本不足不可评估
kick_periodicity_peak_detected                  1=检测到峰 / 0=样本充分但 weak_or_no_peak / null=不可评估

summary.head_motion_spike_frames.details
  .spike_count                                 head_motion_spike_count
spike_count / sample_count                     head_motion_spike_rate

summary.head_body_synchrony.value              head_body_synchrony

summary.head_vertical_range_px.value
÷ reference_body_length.value_px               head_vertical_range_ratio
```

固定像素阈值不可用于规则，因为当前 schema 明确区分 pixel、normalized body length、screen horizontal 等参考基准。

### Decision 4：规则阈值是工程启发式，不是运动科学常模

规则文件必须声明：

```yaml
output_kind: review_finding
threshold_basis:
  id: project_heuristic_v1
  validated: false
  description: >
    基于当前项目样本设定的第一版复核触发值，
    仅用于筛选需要教练查看的片段，不代表运动科学常模。
```

生成的每条 finding 都携带：

```text
threshold_basis = project_heuristic_v1
status = review_required
```

报告后续不得把这些阈值写成“标准范围”。

## 3. 第一版规则包

文件：

```text
backend/app/services/diagnostics/rules/
  side_2d_kinematics_v1.yaml
```

建议初始规则如下。阈值需要在真实 fixture 上跑通后，再由教练确认。

| ID     | 输出发现             | 主要条件                                    |
| ------ | ---------------- | --------------------------------------- |
| KRF001 | 疑似身体轴角波动较大       | `body_angle_std_deg >= 3.5`             |
| KRF002 | 疑似髋部垂直波动较大       | `hip_vertical_range_ratio >= 0.06`      |
| KRF003 | 疑似肘关节活动范围异常      | `elbow_rom_combined_deg < 35` 或 `> 120` |
| KRF004 | 疑似左右肘运动范围差异较大    | 差值 `>=20°` 且差异率 `>=25%`                 |
| KRF005 | 疑似膝关节屈曲幅度较大      | 左右膝 P05 最小值 `<=120°`                    |
| KRF006 | 疑似踝部摆动规律性不足      | 见下方 KRF006 条件（区分无周期峰）                  |
| KRF007 | 疑似头部出现明显位置突变     | spike 数 `>=2` 或 spike rate `>=5%`       |
| KRF008 | 可能存在头部与躯干同步波动    | `r>=0.65` 且头部波动比 `>=4%`                 |

注意级别可以使用更严格的第二阈值：

```text
KRF001 high: std >= 5.0°
KRF002 high: range ratio >= 0.10
KRF003 high: ROM < 25° 或 > 140°
KRF004 high: asymmetry >= 30°
KRF005 high: minimum knee P05 <= 105°
KRF006 high: periodicity score < 0.35
KRF007 high: spike count >= 4
KRF008 high: r >= 0.80 且 range ratio >= 0.06
```

### KRF006 条件（区分样本不足与无稳定周期峰）

`kick_periodicity` 在"未检测到有效周期峰值"时，往往输出
`value=null / availability=unavailable / details.reason=weak_or_no_peak`。
若按 R2 直接跳过，则**最不规律的片段反而不会生成 KRF006**。

Adapter 据此派生两个稳定键：

```python
if sample_count < required_minimum:
    kick_periodicity_evaluable = 0
    kick_periodicity_peak_detected = None
elif details.reason == "weak_or_no_peak":
    kick_periodicity_evaluable = 1
    kick_periodicity_peak_detected = 0
else:
    kick_periodicity_evaluable = 1
    kick_periodicity_peak_detected = 1
```

KRF006 条件改为：

```yaml
required_metrics:
  - kick_periodicity_evaluable

condition:
  any:
    - all:
        - metric: kick_periodicity_evaluable
          op: "=="
          value: 1
        - metric: kick_periodicity_peak_detected
          op: "=="
          value: 0
    - metric: kick_periodicity_score
      op: "<"
      value: 0.45
```

- `kick_periodicity_evaluable == 0` → 视为样本不足，`unavailable_metric` 跳过（R2）。
- `evaluable == 1 and peak_detected == 0` → 样本充分但无稳定周期峰，本身就是待复核证据，生成 finding。
- `kick_periodicity_score < 0.45` → 正常低规律性，生成 finding。

## 4. 规则示例

```yaml
schema_version: swim-review-rules.v1
rule_set: side_2d_kinematics_v1
output_kind: review_finding

source:
  calculator: side_2d_kinematics
  metric_schema: swim-side-kinematics.v1

threshold_basis:
  id: project_heuristic_v1
  validated: false

rules:
  - id: KRF005
    code: large_knee_flexion_review
    title: 疑似膝关节屈曲幅度较大
    category: lower_limb
    status: active
    enabled: true

    required_metrics:
      - minimum_knee_p05_deg

    condition:
      all:
        - metric: minimum_knee_p05_deg
          op: "<="
          value: 120

    attention_level:
      high:
        all:
          - metric: minimum_knee_p05_deg
            op: "<="
            value: 105
      medium:
        all:
          - metric: minimum_knee_p05_deg
            op: "<="
            value: 120

    priority_base: 70

    evidence_metric_keys:
      - minimum_knee_p05_deg
      - left_knee_p05_deg
      - right_knee_p05_deg
      - knee_rom_left_deg
      - knee_rom_right_deg

    evidence_frame_strategy:
      resolver: knee_minimum_triggering_side
      limit: 1

    limitations:
      - 当前结果来自侧面二维投影
      - 未识别具体打腿动作阶段
      - 关节角度可能受身体转动和遮挡影响

    review_question: >
      请结合证据帧确认是否存在以膝关节屈伸为主、
      而不是以髋部带动为主的打腿模式。
```

## 5. 证据帧选择

规则是否命中，只能由已持久化 metrics 决定。证据帧解析器可以读取 time series 和 NormalizedAnnotation，但只能用于“找画面”，不得重新计算触发值。

选择策略：

```text
KRF001
→ body_axis_angle_deg 序列中偏离中位数最大的 1–2 帧

KRF002
→ canonical hip midpoint 的最高与最低帧

KRF003
→ 触发侧肘角最小帧和最大帧

KRF004
→ 左右侧各自 ROM 的边界帧

KRF005
→ 触发侧膝角最小帧

KRF006
→ 踝部相对轨迹的相邻峰值和谷值

KRF007
→ head_motion_spike_frames 中前 3 帧

KRF008
→ 头部与躯干一阶位移同时最大的帧
```

证据帧策略 SHALL 用**显式 resolver 枚举**表达，不引入泛化的 `metric_key` + `side` DSL：
YAML 直接写稳定 resolver 名，由 `EvidenceResolver` 内部映射到具体 time series 键。
第一版仅 8 条规则，避免 YAML 演变成另一门复杂 DSL。

```yaml
evidence_frame_strategy:
  resolver: knee_minimum_triggering_side   # KRF005
  resolver: body_axis_max_deviation        # KRF001
  resolver: hip_high_low                   # KRF002
  resolver: elbow_min_max_triggering_side  # KRF003
  resolver: elbow_asymmetry_bounds         # KRF004
  resolver: ankle_peak_trough              # KRF006
  resolver: head_spike_first_n             # KRF007
  resolver: head_trunk_sync_max            # KRF008
  limit: 1   # 每条 finding 证据帧上限为 3
```

即使 source-video mapping 未验证，也保留 annotation frame：

```json
{
  "annotation_frame": 34,
  "source_video_frame": null,
  "extractable": false,
  "mapping_status": "unverified"
}
```

此时发现仍然可生成，但必须增加：

```text
无法自动截取原视频证据帧，当前仅可定位标注帧。
```

## 6. 置信度规则

每条 finding 的 confidence 不是 YAML 中写死，而是从引用指标计算：

```text
source confidence
= 所有 required metric confidence 的最小值

availability factor:
available       = 1.00
low_confidence  = 0.65
unavailable     = 不执行规则

finding confidence
= min(source confidence × availability factor)
```

置信度等级：

```text
high    >= 0.80
medium  >= 0.50
low     < 0.50
```

规则命中低置信度指标时：

* finding 仍然保留；
* `status` 仍是 `review_required`；
* 增加 `部分证据指标可信度较低` limitation；
* 排序分数下降；
* 不升级成确定性结论。

### 排序权重（可执行定义）

```text
attention_weight:
  high   = 1.00
  medium = 0.70
  low    = 0.40

priority_score =
  priority_base
  × attention_weight
  × confidence
```

稳定排序（tie-breaker）：

```text
priority_score DESC
attention_level DESC   （high > medium > low）
rule_id ASC
```

## 7. 幂等生成

```text
generation_signature = SHA256(
    annotation_metric_id
    + source_annotation_revision
    + source_metric_hash
    + rule_set
    + rule_file_hash
    + engine_version
    + threshold_basis
)
```

行为：

```text
相同 signature + force=false
→ 返回已有 finding set

相同 signature + force=true
→ 原地重新生成

metric 内容或规则文件变化
→ signature 变化，创建新的 finding set
```

生成前必须验证：

```text
metric.calculator == side_2d_kinematics
metric.schema_version == swim-side-kinematics.v1
metric.source_revision == normalized_annotation.revision
```

## 8. API

`rule_set` 通过 query 参数选择，默认 `side_2d_kinematics_v1`。generation signature 含
`rule_set`，故 GET 也需携带相同参数以计算 expected signature（见 R5）。

```http
POST /api/v1/annotation-metrics/{id}/review-findings/generate?rule_set=side_2d_kinematics_v1&force=false
GET  /api/v1/annotation-metrics/{id}/review-findings?rule_set=side_2d_kinematics_v1
```

错误码（已删除 `no_reviewable_metrics`，与 R2 一致）：

```text
404 metric_unavailable
404 review_findings_not_generated

409 metric_revision_stale

422 unsupported_metric_schema
422 invalid_metric_payload
422 invalid_rule_set
422 rule_output_kind_mismatch

500 review_findings_generation_failed
```

合法空结果分三种，不可混为一谈：

```json
// 1) 规则全部正常评估，但无命中
{ "findings": [], "skipped_rules": [], "warnings": [] }

// 2) 没有足够数据判断（所有 required 指标 unavailable）
{
  "findings": [],
  "skipped_rules": [
    {"id": "KRF006", "reason": "unavailable_metric:kick_periodicity_evaluable"}
  ],
  "warnings": ["no_evaluable_review_rules"]
}

// 3) 有数据但未达阈值（可省略 warning，避免把"未发现问题"写成异常）
{ "findings": [], "skipped_rules": [], "warnings": [] }
```

---

# Resolved decisions after implementation review

> 以下六项在探索阶段经代码核查后定案。原方案架构不变，仅把边界、跳过语义、
> 幂等/读取语义与双引擎边界写死，避免实现阶段歧义。

## R1. 直接复用现有条件评估器，不复制

`Side2DKinematicsReviewAdapter` SHALL 通过 `DiagnosticMetricsContext` 暴露派生标量指标。
`KinematicReviewFindingsEngine` SHALL 复用 `evaluate_trigger` 与 `evaluate_severity_branch`，
SHALL NOT 复制结构化条件评估器。

```python
# review 模块内部类型别名
ReviewRuleContext = DiagnosticMetricsContext
```

```text
condition
→ evaluate_trigger

attention_level.high / medium / low
→ evaluate_severity_branch
```

`DiagnosticMetricsContext` 名称虽偏旧，但本轮不做横向重命名重构；后续若规则系统继续扩展，
再单独泛化为 `RuleEvaluationContext`。

## R2. 缺失 / 不可用 / 低置信 / 未命中 四态分流

| 输入状态                      | 规则行为    | 输出位置                       |
| ------------------------- | ------- | -------------------------- |
| 逻辑键不存在                    | 跳过      | `missing_metric:<key>`     |
| envelope 为 unavailable    | 跳过      | `unavailable_metric:<key>` |
| envelope 为 low_confidence | 继续评估    | 置信度乘 0.65，并增加 limitation   |
| 指标 available，但条件不成立       | 正常未命中   | 不进入 skipped_rules          |
| 条件成立                      | 生成 finding | `status=review_required`   |

```text
required key 是否存在
  ├─ 否 → skipped: missing_metric
  └─ 是
       ↓
availability 是否 unavailable
  ├─ 是 → skipped: unavailable_metric
  └─ 否
       ↓
评估 condition
  ├─ false → 正常未命中
  └─ true → 生成 finding
```

取消原方案中的 `422 no_reviewable_metrics`：只要输入是合法的
`swim-side-kinematics.v1`，即使所有规则都因数据不足被跳过，也返回：

```json
{
  "status": "ready",
  "findings": [],
  "skipped_rules": [
    { "id": "KRF006", "reason": "unavailable_metric:kick_periodicity_score" }
  ],
  "warnings": ["no_evaluable_review_rules"]
}
```

`422` 只保留给：calculator/schema 不匹配、metrics 顶层结构损坏、
source revision stale、规则包格式非法。这样"没发现问题"与"没足够数据判断"不混为一谈。

## R3. 证据解析双来源：持久化序列优先，标注回退

`EvidenceResolver` SHALL 优先使用 `AnnotationMetric.metrics.time_series`。
当所需位置序列未持久化时，MAY 从 `NormalizedAnnotation` 重建该序列以定位证据帧。
它 MUST NOT 重新计算或覆盖用于触发规则的指标值。

```text
EvidenceResolver MAY reconstruct positional sequences from NormalizedAnnotation
solely for locating evidence frames. It MUST NOT recompute or override the
metric values used to trigger a finding.
```

各规则证据帧来源（已核查：calculator 输出含完整 time_series / ranges /
representative_frames，且图表服务已直接从 metric.metrics["time_series"] 读取）：

| 规则                | 证据帧来源                              |
| ----------------- | ---------------------------------- |
| KRF001 身体轴角波动     | `time_series.body_axis_angle_deg`  |
| KRF002 髋部垂直波动     | 从 NormalizedAnnotation 重建髋中点 y     |
| KRF003 肘 ROM 异常   | 左右肘角 time series                   |
| KRF004 左右肘 ROM 差异 | 左右肘角 time series                   |
| KRF005 膝关节屈曲较大    | 左右膝角 time series                   |
| KRF006 踝部规律性不足    | 从标注重建分侧踝—髋相对轨迹                     |
| KRF007 头部位置突变     | `head_motion_spike_frames.details` |
| KRF008 头躯干同步波动    | 头部和躯干逐帧 y 序列                       |

说明：身体姿态目前仅把身体轴与躯干轴写入 time series，髋部 y 仅用于计算极差、未单独持久化，
故 KRF002 需回读标注；踝部相对轨迹虽进入 time series，但左右两侧合并为同一键、无稳定 `side`
字段，故 KRF006 也更适合从标准化标注重建分侧序列。

## R4. force 与原地覆盖相同 signature

不需要取消 `force`，但必须定义为**原地覆盖相同 signature 的记录**。

```text
相同 signature + force=false
→ 返回已有记录，不重新运行

相同 signature + force=true
→ 将已有记录重置为 generating
→ 原地重新运行并覆盖 findings
→ 不 INSERT 新行

不同 signature
→ 创建新的 finding set
→ 保留旧版本供追溯
```

唯一约束仍然合理：

```text
UNIQUE(annotation_metric_id, generation_signature)
```

## R5. 当前 GET 按 expected signature 解析

GET 接口 SHALL NOT 简单地按 `created_at DESC` 返回最新一条（否则可能返回旧规则版本）。

```text
GET /annotation-metrics/{id}/review-findings?rule_set=side_2d_kinematics_v1

1. 根据当前 metric、rule_set、当前规则文件、当前 engine version
   计算 expected_generation_signature
2. 返回与 expected signature 完全匹配的 finding set
3. 不存在则返回 404 review_findings_not_generated
```

历史查询以后单独提供：

```http
GET /annotation-metrics/{id}/review-findings/history
```

下游报告永远不该误拿旧规则版本生成的结果（这是 Change 6 报告消费契约的前置条件）。

## R6. 诊断引擎与复核引擎必须分开

不要让 `RuleBasedDiagnosticsEngine.run()` 按 `output_kind` 分支返回两种输出类型。

```text
共享：
  RuleRegistry
  evaluate_trigger
  evaluate_severity_branch
  template formatting

旧链路：
  RuleBasedDiagnosticsEngine
  → DiagnosticsOutput
  → DiagnosticItem

新链路：
  KinematicReviewFindingsEngine
  → ReviewFindingsOutput
  → KinematicReviewFinding
```

`RuleRegistry` 加载 YAML 后读取 `output_kind: review_finding`。
两个引擎都要校验 rule set 类型：

```text
RuleBasedDiagnosticsEngine   只接受 output_kind = diagnostic
KinematicReviewFindingsEngine 只接受 output_kind = review_finding
```

传错规则包时明确报错：`rule_output_kind_mismatch`。这能防止
`side_freestyle_v1` 与 `side_2d_kinematics_v1` 被错误地交给对方执行。

## R7. 红线自动检查（内容护栏，不替代人工审核）

禁止确定性断言短语（硬校验 / failure 级）：

```python
FORBIDDEN_ASSERTIVE_PHRASES = [
    "力量不足",
    "核心能力不足",
    "推进力不足",
    "推进效率低",
    "上肢支撑能力不足",
    "说明运动员",
    "证明运动员",
    "导致阻力增加",
    "必然影响",
]
```

正向格式约束：

```text
title 必须以“疑似”或“可能”开头            （硬校验 / failure 级）
review_question 必须包含                  （软校验 / warning 级）
  “请结合原视频确认” 或 “请教练复核”
每条 finding 必须至少包含                  （硬校验 / failure 级）
  “侧面二维投影” 或 “未结合动作阶段” 等限制说明
```

禁用短语硬校验的扫描范围 SHALL 仅限于 `title`、未来可能增加的 `conclusion` 与 `reason`
字段，**不扫描** `limitations` 与 `review_question`**。原因：limitation 中可能有否定性
合法表达（如"当前二维数据不能用于判断推进效率低的问题"），整句含"推进效率低"但语义是否定。
`limitations` / `review_question` 仅做人工审核或 warning 级检查。

注意：禁用词表不可过宽——"效率"等词在 limitation 中可能有合法表达
（如"当前二维数据不能用于判断推进效率"），因此只禁具体断言短语，不禁整词。
