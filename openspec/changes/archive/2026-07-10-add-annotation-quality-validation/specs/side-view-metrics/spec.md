# side-view-metrics Specification (Delta)

## MODIFIED Requirements

### Requirement: Quality level and degradation
系统 SHALL 输出 `MetricQualityReport`（含 status、metric_availability、issues 数组），代替当前平铺的 level/warnings/computed_metric_count/skipped_metric_count。输出位置保持 `AnnotationMetric.quality`。

#### Scenario: Missing waterline degrades hip_depth
- **WHEN** annotation 缺 `reference_lines.waterline`
- **THEN** `hip_depth_cm` MUST 为 null，quality.status=warning，issues 含 `WATERLINE_MISSING`

#### Scenario: Missing fps or core keypoints is error
- **WHEN** 缺 `fps` 或缺核心关键点或 keypoint_frames < 3
- **THEN** `quality.status` MUST 为 `warning`（非 error——annotation quality 已在前置验证中标记 invalid），相关指标为 `unavailable`

## ADDED Requirements

### Requirement: Metric availability per indicator
`MetricQualityReport.metric_availability` SHALL 为每个指标提供 `available / low_confidence / unavailable` 状态。

#### Scenario: Computed metric is available
- **WHEN** 某指标成功计算且有足够有效样本（>= 3）
- **THEN** 该指标的 `metric_availability` MUST 为 `available`

#### Scenario: Low sample count is low_confidence
- **WHEN** 某指标虽成功计算但仅 1 个有效样本
- **THEN** 该指标的 `metric_availability` MUST 为 `low_confidence`，issues 含相应 code

#### Scenario: Failed computation is unavailable
- **WHEN** 某指标因缺少输入数据无法计算
- **THEN** 该指标的 `metric_availability` MUST 为 `unavailable`

### Requirement: Metric quality issues reference specific metrics
`MetricQualityReport.issues[]` SHALL 包含 `code`、`metric`（指标名）、`severity`、`message`，定位到具体指标而非笼统说明。

#### Scenario: Low sample issue references metric name
- **WHEN** 肘角样本不足
- **THEN** issue MUST 包含 `metric: "elbow_angle_deg_avg"` 和 `code: "ELBOW_ANGLE_SAMPLE_LOW"`
