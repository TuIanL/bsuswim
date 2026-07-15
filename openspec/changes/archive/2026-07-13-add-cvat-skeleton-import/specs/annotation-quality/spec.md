# annotation-quality Specification

## ADDED Requirements

### Requirement: CVAT source without events is warning not invalid
当 `source = "cvat"` 且 `events` 为空时，quality checker SHALL 标记为 warning 而非 invalid，按指标级可用性聚合模块 readiness。

#### Scenario: CVAT source with empty events yields warning
- **WHEN** `source = "cvat"`，keypoint_frames 完整且有效，但 events 为空
- **THEN** `quality.status` MUST 为 `warning`

### Requirement: Indicator-level availability over module-level
quality profile SHALL 按具体指标声明依赖，指标 availability 聚合为模块 readiness。不按大模块笼统声明 availability。

#### Scenario: CVAT source keypoints only, metric level
- **WHEN** `source = "cvat"`，只有 keypoint_frames，无 events 无 scale，有 timestamp_sec
- **THEN** 肘角膝角指标 MUST 为 `ready`，wrist_speed_px_per_s MUST 为 `ready`，wrist_speed_m_per_s MUST 为 `blocked`（缺 scale），stroke_rate MUST 为 `blocked`（缺 cycle 边界事件）

#### Scenario: Module aggregated from indicators
- **WHEN** `body_position` 模块的所有核心指标（身体轴角度）为 `ready`
- **THEN** `body_position` readiness MUST 为 `ready`

#### Scenario: Module partially degraded
- **WHEN** `efficiency` 模块中 speed_px_per_s 为 `ready` 但 speed_m_per_s 为 `blocked`
- **THEN** `efficiency` readiness MUST 为 `degraded`，包含可用子集清单

### Requirement: Indicator availability matrix for source=cvat
以下为 `source=cvat` 场景下的指标级可用性矩阵：

| 指标 | 必需条件 |
|------|---------|
| elbow_angle_deg, knee_angle_deg | 对应关键点 visible |
| body_axis_angle | 肩、髋关键点 |
| hip_depth_px | 髋点 |
| hip_depth_cm | 髋点 + waterline + scale |
| wrist_trajectory_shape | 连续 wrist 关键点 |
| wrist_speed_px_per_s | 关键点 + timestamp_sec |
| wrist_speed_m_per_s | 关键点 + timestamp_sec + scale |
| stroke_cycle_duration | cycle 边界事件 + timestamp_sec |
| stroke_rate | cycle 边界事件 + timestamp_sec |
| stroke_length | cycle 边界 + scale |
| swolf | distance + time + stroke_count |

#### Scenario: Scale absent blocks physical speed and distance
- **WHEN** `scale` 缺失
- **THEN** `wrist_speed_m_per_s`、`hip_depth_cm`、`stroke_length`、`swolf` MUST 为 `blocked`；`elbow_angle_deg`、`wrist_speed_px_per_s` MUST 仍为 `ready`

#### Scenario: Events absent blocks cycle-based metrics
- **WHEN** `events` 为空
- **THEN** `stroke_cycle_duration`、`stroke_rate`、`stroke_length`、`swolf` MUST 为 `blocked`

### Requirement: Unverified time mapping blocks time metrics
当 `frame_mapping.verified = false` 或 `mode = "unknown"` 时，依赖 `timestamp_sec` 的指标 SHALL 标记为 blocked。

#### Scenario: v2 unverified blocks time metrics
- **WHEN** `schema_version = "swim-annotation.v2"` 且 `frame_mapping.verified = false`
- **THEN** `wrist_speed_px_per_s`、`wrist_speed_m_per_s`、`stroke_cycle_duration`、`stroke_rate` MUST 为 `blocked`，`elbow_angle_deg` MUST 仍为 `ready`，quality warnings 包含 `TIME_MAPPING_UNVERIFIED`

#### Scenario: Verified time mapping enables timing metrics
- **WHEN** `frame_mapping.verified = true` 且其他条件满足
- **THEN** 时间类指标 readiness MUST 根据各自必需条件正常评估

### Requirement: v1 compatibility for time metrics
`swim-annotation.v1` 时间类指标继续使用 `frame / fps` 兼容计算，不受 v2 `verified` 规则影响。

#### Scenario: v1 time metrics computed via frame/fps
- **WHEN** `schema_version = "swim-annotation.v1"`
- **THEN** 时间类指标 SHALL 使用 `frame / fps` 推导时间戳，不受 `frame_mapping.verified` 影响

### Requirement: Unannotated frames do not trigger missing point errors
`annotation_sequence.frame_count` 与 `annotated_frame_count` 的差值 SHALL 视为"未标注帧"，而非"标注缺失帧"，不触发错误级别的 quality issue。

#### Scenario: 56 annotated out of 356 total is warning
- **WHEN** `annotated_frame_count = 56`，`annotation_sequence.frame_count = 356`
- **THEN** quality MUST 为 `warning` 而非 `invalid`，issue 为 `SEQUENCE_COVERAGE_LOW`（info 级别）

#### Scenario: Analysis range fully covered
- **WHEN** `analysis_ranges` 声明范围为 0–55，`annotated_frame_count = 56`
- **THEN** 覆盖率 MUST 视为 100%，不生成 `SEQUENCE_COVERAGE_LOW` issue

### Requirement: Kinovea source unchanged
`source = "kinovea"` 的 quality 评估规则 SHALL 不受 CVAT 新增规则影响。

#### Scenario: Kinovea rules unchanged
- **WHEN** `source = "kinovea"`
- **THEN** quality checker MUST 使用现有规则，不应用 CVAT 来源的 availability 矩阵
