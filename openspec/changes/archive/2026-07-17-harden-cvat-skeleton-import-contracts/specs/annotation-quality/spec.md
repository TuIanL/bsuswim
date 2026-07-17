## ADDED Requirements

### Requirement: TIME_MAPPING_UNVERIFIED applies to all unverified modes

`check_frame_mapping()` SHALL 对所有 `verified=false` 的 frame mapping 产生 `TIME_MAPPING_UNVERIFIED` issue，无论 mode 为何。

#### Scenario: explicit + false produces warning
- **WHEN** `frame_mapping.mode = "explicit"` 且 `verified = false`
- **THEN** quality checker MUST 添加 `TIME_MAPPING_UNVERIFIED` warning

#### Scenario: unknown + false produces warning
- **WHEN** `frame_mapping.mode = "unknown"` 且 `verified = false`
- **THEN** quality checker MUST 添加 `TIME_MAPPING_UNVERIFIED` warning

#### Scenario: verified = true passes
- **WHEN** `frame_mapping.verified = true`
- **THEN** quality checker MUST 不产生 `TIME_MAPPING_UNVERIFIED` issue，无论 mode

### Requirement: FPS_UNVERIFIED issue for unverified FPS

系统 SHALL 新增 `FPS_UNVERIFIED` issue code，在 `video.fps_verified = false` 时产生。

#### Scenario: Unverified FPS produces warning
- **WHEN** `video.fps_verified = false`
- **THEN** quality checker MUST 添加 `FPS_UNVERIFIED` issue，时间类指标 blocked

#### Scenario: Verified FPS no warning
- **WHEN** `video.fps_verified = true`
- **THEN** quality checker MUST 不产生 `FPS_UNVERIFIED` issue

### Requirement: Time metrics blocked unless mapping and FPS verified (except direct timestamp)

时间类指标（速度、划频、周期时长）SHALL 遵循两条规则：
- **从 manifest 直接提供 timestamp_sec**：仅需 `mapping.verified=true`，不依赖 fps_verified
- **从 source_video_frame 派生**：需 `mapping.verified=true` 且 `fps_verified=true`

#### Scenario: Direct timestamp enabled with unverified FPS
- **WHEN** manifest 直接提供 `timestamp_sec` 且 `mapping.verified=true`，但 `fps_verified=false`
- **THEN** 时间类指标 MUST 仍可评估

#### Scenario: Derived timestamp blocked by unverified FPS
- **WHEN** manifest 仅提供 `source_video_frame`，`mapping.verified=true` 但 `fps_verified=false`
- **THEN** 时间类指标 MUST 标记为 `blocked`

#### Scenario: Either unverified mapping blocks both paths
- **WHEN** `frame_mapping.verified=false`
- **THEN** 所有时间类指标 MUST 标记为 `blocked`
- **AND** 角度类、轨迹类等非时间指标 MUST 仍保持可用

### Requirement: ANALYSIS_RANGE_NOT_COVERED blocking issue

系统 SHALL 新增 `ANALYSIS_RANGE_NOT_COVERED` issue code，在 analysis_ranges 未被 annotated_ranges 完整覆盖时产生，其 severity 为 error、blocking=true。

`check_sequence_coverage()` SHALL 同时保留 `SEQUENCE_COVERAGE_LOW`（info，非 blocking）和新增的 `ANALYSIS_RANGE_NOT_COVERED`（error，blocking），两者互相独立。

#### Scenario: Analysis range fully covered by annotated ranges
- **WHEN** `analysis_ranges = [{start_annotation_frame: 100, end_annotation_frame: 120}]`
- **AND** `annotated_ranges` 包含 `[{start_annotation_frame: 100, end_annotation_frame: 120}]`
- **THEN** 覆盖率检查 MUST 通过，不产生 `SEQUENCE_COVERAGE_LOW` 或 `ANALYSIS_RANGE_NOT_COVERED`

#### Scenario: Analysis range not covered despite equal counts
- **WHEN** `analysis_ranges = [{start_annotation_frame: 100, end_annotation_frame: 120}]`（21 帧）
- **AND** `annotated_frame_count = 21` 但 `annotated_ranges` 为 `[{start_annotation_frame: 0, end_annotation_frame: 20}]`
- **THEN** 覆盖率检查 MUST 产生 `ANALYSIS_RANGE_NOT_COVERED`（blocking=true）
- **AND** MUST NOT 仅因帧数相等而通过

#### Scenario: No analysis ranges defaults to annotated ranges check
- **WHEN** `analysis_ranges` 为空
- **THEN** 覆盖率检查 MUST 使用 `annotated_frame_count / annotation_sequence.frame_count` 计算覆盖率
- **AND** 不产生 `ANALYSIS_RANGE_NOT_COVERED`

## MODIFIED Requirements

### Requirement: Unverified time mapping blocks time metrics

当 `frame_mapping.verified = false` 或（时间来源为 source_video_frame 派生时 `video.fps_verified = false`）时，依赖 `timestamp_sec` 的指标 SHALL 标记为 blocked。

#### Scenario: Unverified mapping blocks time metrics
- **WHEN** `frame_mapping.verified = false`
- **THEN** `wrist_speed_px_per_s`、`wrist_speed_m_per_s`、`stroke_cycle_duration`、`stroke_rate` MUST 为 `blocked`
- **AND** `elbow_angle_deg` MUST 仍为 `ready`
- **AND** quality warnings 包含 `TIME_MAPPING_UNVERIFIED`

#### Scenario: Verified mapping with verified FPS enables timing
- **WHEN** `frame_mapping.verified = true` 且 `fps_verified = true` 且其他条件满足
- **THEN** 时间类指标 readiness MUST 根据各自必需条件正常评估

#### Scenario: Direct timestamp bypasses FPS check
- **WHEN** manifest 直接提供 `timestamp_sec` 且 `mapping.verified = true`
- **THEN** 时间类指标 MUST 可正常评估，即使 `fps_verified = false`
