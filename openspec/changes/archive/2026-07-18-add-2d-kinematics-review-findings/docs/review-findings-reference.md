# 二维运动学复核发现：派生键、阈值基础、限制分类与报告消费契约

> 配套 Change `add-2d-kinematics-review-findings`。本文件集中记录实现中产生的
> 事实约定，供后续维护与 Change 6 报告装配参考。

## 1. 派生上下文键（adapter 产出）

规则 YAML 只消费以下稳定逻辑键。键名由 `Side2DKinematicsReviewAdapter` 从
`swim-side-kinematics.v1` 的 `MetricEnvelope` 展平/派生而来。

### 直接透传（来自 summary）

| 逻辑键 | 来源 | 单位 |
| --- | --- | --- |
| `body_angle_std_deg` | `summary.body_angle_std_deg` | deg |
| `posture_stability_cv` | `summary.posture_stability_cv` | % |
| `head_body_synchrony` | `summary.head_body_synchrony` | r |
| `head_vertical_range_px` | `summary.head_vertical_range_px` | px |

### 肘 ROM 细节展平

| 逻辑键 | 来源 | 单位 |
| --- | --- | --- |
| `elbow_rom_left_deg` | `summary.elbow_rom_deg.details.left` | deg |
| `elbow_rom_right_deg` | `summary.elbow_rom_deg.details.right` | deg |
| `elbow_rom_combined_deg` | `summary.elbow_rom_deg.details.combined` | deg |
| `elbow_rom_asymmetry_deg` | `abs(left - right)` | deg |
| `elbow_rom_asymmetry_ratio` | `abs(left-right) / max(left,right)` | ratio |

### 膝 P05 展平 + 最小侧

| 逻辑键 | 来源 | 单位 |
| --- | --- | --- |
| `left_knee_p05_deg` | `ranges.left_knee_angle_deg.p05` | deg |
| `right_knee_p05_deg` | `ranges.right_knee_angle_deg.p05` | deg |
| `minimum_knee_p05_deg` | `min(left, right)` | deg |

### 踢腿周期性

| 逻辑键 | 来源 | 单位 |
| --- | --- | --- |
| `kick_periodicity_score` | `summary.kick_periodicity.value.score` | score |
| `kick_period_frames` | `summary.kick_periodicity.value.period_frames` | frame |
| `kick_periodicity_evaluable` | `sample_count >= 24` 派生 | — |
| `kick_periodicity_peak_detected` | 无峰或 value=None → 0；否则 1 | — |

`kick_periodicity_evaluable==0` 表示样本不足（unavailable 跳过）；`==1 and peak_detected==0`
表示样本充分但无稳定周期峰（本身即待复核证据）。

### 头部尖峰

| 逻辑键 | 来源 | 单位 |
| --- | --- | --- |
| `head_motion_spike_count` | `summary.head_motion_spike_frames.details.spike_count` | count |
| `head_motion_spike_rate` | `spike_count / sample_count` | ratio |

### 参考体长归一化（禁止固定像素阈值）

| 逻辑键 | 来源 | 单位 |
| --- | --- | --- |
| `hip_vertical_range_ratio` | `hip_vertical_range_px / reference_body_length.value_px` | ratio |
| `head_vertical_range_ratio` | `head_vertical_range_px / reference_body_length.value_px` | ratio |

派生指标可信度传播规则：
- `availability = 所有来源指标中最差的 availability`
- `confidence = 所有来源指标 confidence 的最小值`

### 膝/肘 ROM（用于 evidence 展示，非触发键）

`knee_rom_left_deg` / `knee_rom_right_deg` 来自 `summary.knee_rom_deg.details`。

## 2. 阈值基础（threshold basis）

所有规则文件声明：

```yaml
threshold_basis:
  id: project_heuristic_v1
  validated: false
```

含义：第一版复核触发值基于当前项目样本设定，仅用于筛选需教练查看的片段，
**不代表运动科学常模**。每条 finding 携带 `threshold_basis = project_heuristic_v1`。
报告后续不得把这些阈值写成"标准范围"。

## 3. 限制分类（limitation taxonomy）

每条 finding 的 `limitations` 至少包含以下维度之一：

- **投影维度**：当前结果来自侧面二维投影
- **阶段维度**：未识别具体泳姿/打腿/划水阶段
- **遮挡维度**：关节角度可能受身体转动和遮挡影响
- **方法维度**：已按参考体长归一化 / 未结合动作阶段判断
- **因果维度**：相关性不表示因果关系（KRF008）

低置信度证据额外追加：`部分证据指标可信度较低`。

## 4. Change 6 报告消费契约（前置条件）

- 报告只应消费 `GET /annotation-metrics/{id}/review-findings?rule_set=...` 的返回，
  该接口按 **expected generation signature** 解析，不会返回旧规则版本生成的结果。
- 报告 MUST NOT 假设 findings 按 `created_at DESC` 取最新；必须携带与生成时一致的 `rule_set`。
- 每条 finding 的 `status` 恒为 `review_required`，报告 MUST 明确标注"待复核"，
  不得呈现为确定性诊断。
- 证据帧 `extractable=false` 时，报告只能定位标注帧，不得声称已截取原视频。
- 红线：报告不得把 `title`/`review_question`/`limitations` 改写为力量、能力或推进效率不足
  的确定性结论。
