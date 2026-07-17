## Context

当前系统已存在 `side_view_metrics` calculator，但它面向的是带有水面线、标尺、动作事件和距离标记的完整技术分析场景，输入要求包括非分侧关键点命名、语义事件、标尺和距离标记。真实 CVAT 输入主要包含逐帧 COCO17 左右分侧关键点，缺乏事件和标尺。两者输入条件差异过大，需新增独立的 `side_2d_kinematics` calculator。

## Goals / Non-Goals

**Goals:**

- 新增 `side_2d_kinematics` calculator 与旧 calculator 并存
- 从 COCO17 左右分侧关键点计算身体姿态、上肢、下肢、头部/躯干四类指标
- 每个指标输出统一的 MetricEnvelope
- 不依赖事件、标尺、水面线、距离标记或游进方向
- calculator registry 替代硬编码路由
- 支持 `?calculator=` 选择计算器
- 新增 `source_revision` 列，三态 stale 检测
- 保留旧 calculator 及其所有测试和诊断

**Non-Goals:**

- 不删除或重写 side_view_metrics
- 不修改 diagnostics engine、report builder、前端
- 不实现动作阶段识别或周期分割
- 不生成水面夹角、髋部水深或真实速度
- 不判断 kick 时序正确或错误

## Decisions

### D1: New calculator coexists with legacy

| | 旧 | 新 |
|---|---|---|
| schema_version | swim-side-metrics.v1 | swim-side-kinematics.v1 |
| calculator | side_view_metrics | side_2d_kinematics |
| version | 0.1.0 | 1.0.0 |
| 依赖事件/标尺 | 是 | 否 |

### D2: Calculator registry and code organization

目录结构：

```
services/metrics/
├── registry.py              # MetricCalculator protocol + registry
├── protocols.py             # MetricCalculator, MetricCalculationContext
├── engine.py                # legacy side_view_metrics（保持不变）
├── kinematics/
│   ├── calculator.py        # Side2DKinematicsCalculator
│   ├── frame_resolver.py    # CanonicalKinematicFrame
│   ├── geometry.py          # angle helpers (new, not touching old)
│   ├── continuity.py        # continuity factor helpers
│   ├── quality.py           # Side2DKinematicsQualityEvaluator
│   ├── body_posture.py
│   ├── upper_limb.py
│   ├── lower_limb.py
│   └── head_trunk.py
```

Protocol：

```python
class MetricCalculator(Protocol):
    name: str
    version: str
    schema_version: str

    def calculate(
        self,
        annotation: dict,
        context: MetricCalculationContext,
    ) -> dict: ...

@dataclass
class MetricCalculationContext:
    normalized_annotation_id: int
    source_revision: int
    camera_view: str
    annotation_metadata: dict
    frame_mapping: dict | None
    stroke_type: str | None
```

### D3: Top-level output schema

```python
class Side2DKinematicsResult(BaseModel):
    schema_version: str = "swim-side-kinematics.v1"
    calculator: str = "side_2d_kinematics"
    calculator_version: str = "1.0.0"
    camera_view: str = "side"

    source: MetricSourceInfo
    reference_body_length: ReferenceBodyLength | None = None
    summary: dict[str, MetricEnvelope] = Field(default_factory=dict)
    time_series: dict[str, list[MetricSeriesPoint]] = Field(default_factory=dict)
    ranges: dict[str, MetricRange] = Field(default_factory=dict)
    representative_frames: dict[str, RepresentativeFrame] = Field(default_factory=dict)
    quality: dict = Field(default_factory=dict)
```

```python
class MetricSourceInfo(BaseModel):
    normalized_annotation_id: int
    revision: int
    revision_status: Literal["current", "stale", "unknown"] = "unknown"
    frame_mapping_status: Literal["verified", "unverified", "unknown"] = "unknown"
    stroke_type: str | None = None
```

所有可变默认值使用 `Field(default_factory=...)`。

### D4: MetricEnvelope with provenance

```python
class MetricProvenance(BaseModel):
    annotation_frame_ranges: list[list[int]] = Field(default_factory=list)
    source_video_frame_ranges: list[list[int]] = Field(default_factory=list)
    frame_basis: Literal["annotation_frame", "source_video_frame"] = "annotation_frame"
    mapping_status: Literal["verified", "unverified", "unknown"] = "unknown"

class MetricEnvelope(BaseModel):
    key: str
    category: Literal["body_posture", "upper_limb", "lower_limb", "head_trunk"]
    value: float | int | list | dict | None = None
    unit: str | None = None
    sample_count: int = 0
    availability: Literal["available", "low_confidence", "unavailable"] = "unavailable"
    confidence: float = 0.0
    provenance: MetricProvenance = Field(default_factory=MetricProvenance)
    reference_basis: Literal[
        "screen_horizontal", "joint_geometry", "pixel",
        "normalized_body_length", "frame_sequence",
    ] = "screen_horizontal"
    details: dict = Field(default_factory=dict)
```

### D5: source_revision tri-state

```sql
ALTER TABLE annotation_metrics ADD COLUMN source_revision INTEGER NULL;
```

| source_revision | revision_status | is_stale |
|---|---|---|
| NULL | unknown | false |
| == annotation.revision | current | false |
| != annotation.revision | stale | true |

revision_status 在 API 响应中计算，不持久化。

### D6: CanonicalKinematicFrame and construction mode

```python
class ConstructionMode(StrEnum):
    BILATERAL_MIDPOINT = "bilateral_midpoint"
    LEFT_PROXY = "left_proxy"
    RIGHT_PROXY = "right_proxy"
    UNAVAILABLE = "unavailable"
```

每个合成点独立追踪 construction_mode。

**Metric-specific mode signature**：跨帧稳定性指标按 signature 分组：

```
mode_signature = (
    shoulder_mid.construction_mode,
    hip_mid.construction_mode,
    ankle_mid.construction_mode,
)
```

规则：
1. 按 metric 所需合成点建立 signature
2. 将时间序列按 signature 分组
3. 优先选择全 bilateral 的最长连续段
4. 否则选择覆盖率最高的单一 signature
5. 不得拼接多个 signature 计算稳定性、同步性或周期性

### D7: Reference body length

```python
class ReferenceBodyLength(BaseModel):
    value_px: float | None = None
    sample_count: int = 0
    availability: Literal["available", "low_confidence", "unavailable"] = "unavailable"
    confidence: float = 0.0
    source_frames: list[int] = Field(default_factory=list)
```

样本要求：≥ 8 → available, 3–7 → low_confidence, < 3 → unavailable。
依赖基准的指标继承其 confidence 上限。

### D8: Angle helpers (new, not modifying old)

```python
def line_angle_to_screen_horizontal_deg(p1, p2) -> float | None:
    """无方向锐角，范围 0–90°"""
    theta = signed_line_tilt_deg(p1, p2)
    return abs(theta) if theta is not None else None

def signed_line_tilt_deg(p1, p2) -> float | None:
    """带符号倾角，范围 [-90°, 90°)"""
    dx, dy = ...
    theta = degrees(atan2(dy, dx))
    return ((theta + 90.0) % 180.0) - 90.0
```

不修改现有 `angle_to_horizontal()`。

### D9: Continuity factor

| 类型 | continuity_factor |
|---|---|
| 静态帧指标（角度均值、ROM） | 1.0 |
| 相邻差分指标（速度） | valid_delta_count / expected_delta_count |
| 序列型指标（周期、同步） | longest_valid_contiguous_run / total_valid_sample_count |

expected_step 来自 verified frame mapping。

### D10: Stroke context for periodicity

```python
STROKE_PERIODICITY_PROFILES = {
    "freestyle": {"type": "alternating", "lag_range": (6, 30)},
    "backstroke": {"type": "alternating", "lag_range": (6, 30)},
    "butterfly": {"type": "synchronous", "lag_range": (6, 20)},
    "breaststroke": {"type": "asymmetric", "lag_range": (10, 40)},
    "unknown": {"type": "generic", "lag_range": (6, 40)},
}
```

v1 仅为 freestyle 启用 available，其他泳姿和 unknown 一律 low_confidence。

### D11: Periodicity algorithm parameters

- Lag 搜索范围：由 stroke profile 定义
- 最小连续帧：24
- 自相关归一化：zero-mean unbiased
- 有效峰值阈值：≥ 0.30
- 峰值选择：非零 lag 范围内的最大 prominence 峰
- 多个峰时：选择 lag 最小、prominence 最大的峰

`left_right_kick_timing`：positive lag 表示右侧踝序列滞后于左侧踝序列。

### D12: Unified availability rules

```
unavailable：
  value is null
  或 sample_count = 0
  或缺少必需输入点

low_confidence：
  value 可计算，但存在任一：
  - sample_count < required_sample_count
  - confidence < 0.65
  - continuity_factor < 0.70
  - reference_body_length 为 low_confidence
  - mapping 未验证且指标依赖时序
  - stroke_type unknown 且指标依赖泳姿

available：
  value 非空
  且满足所有样本、连续性和置信度要求
```

### D13: Quality evaluator

独立的 `Side2DKinematicsQualityEvaluator`，issue codes：

- METRIC_SAMPLE_INSUFFICIENT
- SINGLE_SIDE_FALLBACK（聚合形式：按 metric + frame range，不逐帧）
- REFERENCE_BODY_LENGTH_INSUFFICIENT
- TEMPORAL_CONTINUITY_LOW
- FRAME_MAPPING_UNVERIFIED
- STROKE_CONTEXT_UNKNOWN
- HEAD_POINTS_INSUFFICIENT
- PERIODICITY_PEAK_WEAK

不检查 scale、waterline、events、distance_markers、swim_direction。

### D14: Representative frames

frame mapping 未验证时保留原始 source_video_frame，标记 mapping_status=unverified, extractable=false。

### D15: GET metrics is extend, not add

扩展现有 `GET /normalized-annotations/{id}/metrics`，增加 `calculator` (default: side_view_metrics) 和 `calculator_version` 参数。未知 calculator 返回 422 `unsupported_metric_calculator`。

## Canonical metric definitions

### Body posture

| key | inputs | frame_formula | summary | unit | reference_basis | min_samples |
|---|---|---|---|---|---|---|
| torso_axis_angle_deg | shoulder_mid, hip_mid | acute(s→h→screen_h) | mean | deg | screen_horizontal | 8 |
| body_axis_angle_deg | shoulder_mid, ankle_mid | acute(s→a→screen_h) | mean | deg | screen_horizontal | 8 |
| hip_vertical_range_px | hip_mid.y | max(y)-min(y) | scalar | px | pixel | 8 |
| shoulder_vertical_range_px | shoulder_mid.y | max(y)-min(y) | scalar | px | pixel | 8 |
| body_angle_std_deg | body_axis_angle_deg ts | std(ts) | scalar | deg | screen_horizontal | 8 |
| posture_stability_cv | body_axis_angle_deg ts | 100×std/abs(mean), guard <1° | scalar | % | screen_horizontal | 8 |

### Upper limb

| key | inputs | frame_formula | summary | unit | reference_basis | min_samples |
|---|---|---|---|---|---|---|
| left_elbow_angle_deg | L_shoulder, L_elbow, L_wrist | joint_angle(L_s, L_e, L_w) | mean | deg | joint_geometry | 5 |
| right_elbow_angle_deg | R_shoulder, R_elbow, R_wrist | joint_angle(R_s, R_e, R_w) | mean | deg | joint_geometry | 5 |
| elbow_rom_deg | L+R elbow ts | P95−P05 per side, combine | {left,right,combined} | deg | joint_geometry | 8 |
| arm_extension_ratio | shoulder → wrist dist | dist / ref_body_length | mean | ratio | normalized_body_length | 5 |
| wrist_velocity_px_per_frame | wrist pos ts | Δdist / Δframe | mean | px/frame | pixel | 6 |

### Lower limb

| key | inputs | frame_formula | summary | unit | reference_basis | min_samples |
|---|---|---|---|---|---|---|
| left_knee_angle_deg | L_hip, L_knee, L_ankle | joint_angle(L_h, L_k, L_a) | mean | deg | joint_geometry | 5 |
| right_knee_angle_deg | R_hip, R_knee, R_ankle | joint_angle(R_h, R_k, R_a) | mean | deg | joint_geometry | 5 |
| knee_rom_deg | L+R knee ts | P95−P05 per side, combine | {left,right,combined} | deg | joint_geometry | 8 |
| ankle_vertical_range_px | ankle.y − hip_mid.y | max(rel_y)-min(rel_y) per side | {left,right} | px | pixel | 8 |
| kick_periodicity | ankle_y_relative ts | autocorrelation | score, period_frames | — | frame_sequence | 24 |
| left_right_kick_timing | L/R ankle_y_relative ts | cross-correlation lag | lag_frames, phase_offset | frame | frame_sequence | 16 |

### Head and trunk

| key | inputs | frame_formula | summary | unit | reference_basis | min_samples |
|---|---|---|---|---|---|---|
| head_vertical_range_px | head_center.y | max(y)-min(y) | scalar | px | pixel | 8 |
| head_shoulder_relative_offset | head_center.y − shoulder_mid.y | mean(offset)/ref_body_length | ratio | — | normalized_body_length | 8 |
| head_body_synchrony | Δhead_center.y, Δtrunk_mid.y | Pearson corr of 1st diff | r | — | frame_sequence | 12 |
| head_motion_spike_frames | head_velocity_zscore | MAD robust_z ≥ 3.5 | frame list | frame | frame_sequence | 8 |
| trunk_vertical_stability | trunk_mid.y (detrended) | std(residual)/ref_body_length | ratio | — | normalized_body_length | 12 |

### Velocity frame basis

wrist_velocity 的 `details` 中记录 frame_basis：

```json
{
  "frame_basis": "source_video_frame",
  "expected_step": 1,
  "actual_delta_count": 48
}
```

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| 单侧代理混入中点序列 | metric-specific mode signature，禁止跨 signature 计算 |
| reference_body_length 样本不足 | 纳入 availability，级联到依赖指标 |
| 泳姿影响周期检测 | v1 仅为 freestyle 启用 available |
| 旧记录 source_revision=NULL 误判 | 三态判断：unknown ≠ stale |
| 测试 fixture 不足阻塞开发 | 阶段 0 生成合成 + 真实 fixture |
| GET metrics 扩展破坏旧调用 | 默认 calculator=side_view_metrics |
