# annotation-time-mapping Specification

## Purpose
定义 CVAT annotation frame 与原始视频帧和绝对时间戳之间的映射关系，消除抽帧偏移和帧率歧义，使 metrics 层以 `timestamp_sec` 为唯一权威时间源。

## ADDED Requirements

### Requirement: Four-mode frame mapping
系统 SHALL 支持四种帧映射模式，通过 `FrameMappingMode` 枚举区分。

#### Scenario: Explicit mode with per-frame mapping
- **WHEN** `frame_mapping.mode = "explicit"`
- **THEN** 系统 MUST 使用 `frame_mapping.entries[]` 中的逐帧 `{annotation_frame, source_video_frame, timestamp_sec}` 记录直接映射

#### Scenario: Affine mode with offset and stride
- **WHEN** `frame_mapping.mode = "affine"` 且 `verified = true`
- **THEN** 系统 MUST 通过 `source_video_frame = offset + annotation_frame * stride` 计算，再以 `timestamp_sec = source_video_frame / video_fps` 计算

#### Scenario: Identity mode
- **WHEN** `frame_mapping.mode = "identity"`
- **THEN** 系统 MUST 视 annotation_frame 等于原视频帧号，`timestamp_sec = annotation_frame / video_fps`

#### Scenario: Unknown mode blocks time metrics
- **WHEN** `frame_mapping.mode = "unknown"`
- **THEN** 系统 MUST 允许创建 NormalizedAnnotation，但禁止计算依赖时间类指标（划频、速度、阶段时长），不阻止姿态类指标

### Requirement: verified requires explicit confirmation
`frame_mapping.verified` SHALL 仅通过两种途径设为 `true`：用户通过 `ParseAnnotationOptions` 显式确认，或 `extraction_manifest` 提供逐帧 `source_video_frame`。

#### Scenario: Filename sequence infers affine but not verified
- **WHEN** 图片文件名连续（如 `scene00032.jpg`、`scene00033.jpg`），无 manifest 且无用户确认
- **THEN** 系统 MUST 推断 `mode = "affine"`，`verified = false`，`verification_reason` 记录 `"inferred_from_filename_sequence"`

#### Scenario: User confirmation sets verified=true
- **WHEN** 用户在 `ParseAnnotationOptions.frame_mapping_override` 中提供 `confirmed = true`
- **THEN** 系统 MUST 将 `verified` 设为 `true`

#### Scenario: Manifest with source_video_frame sets verified=true
- **WHEN** companion JSON 提供逐帧 `source_video_frame` 映射
- **THEN** 系统 MUST 将 `verified` 设为 `true`，mode 设为 `"explicit"`

### Requirement: Unverified mapping is treated as unknown for time metrics
当 `verified = false` 时，即使 mode 为 `affine` 或 `identity`，metrics 层也 SHALL 按 `unknown` 处理，禁止时间类指标计算。

#### Scenario: Unverified affine blocks time metrics
- **WHEN** `frame_mapping.mode = "affine"` 但 `verified = false`
- **THEN** quality checker MUST 在 `issues` 中添加 `TIME_MAPPING_UNVERIFIED` warning，metrics 层把所有时间类指标标记为 `blocked`

### Requirement: timestamp_sec is authoritative time source
metrics 层 SHALL 以 `KeypointFrame.timestamp_sec` 为唯一权威时间源，不依赖 `frame / fps` 或 `annotation_fps`。

#### Scenario: Metrics use timestamp_sec for dt
- **WHEN** metrics 层计算连续帧间的时间差
- **THEN** 系统 MUST 使用 `next_frame.timestamp_sec - current_frame.timestamp_sec`，而非 `1 / annotation_fps`

#### Scenario: Missing timestamp_sec blocks time-dependent metrics
- **WHEN** 任一 KeypointFrame 的 `timestamp_sec` 为 null
- **THEN** 依赖该帧的时间类指标 MUST 标记为 `unavailable`

### Requirement: No fallback to frame/fps for v2 unverified
`swim-annotation.v2` 在 `frame_mapping.verified = false` 时 SHALL 禁止回退到 `frame / video_fps` 兼容计算。

#### Scenario: v2 unverified does not fall back
- **WHEN** schema_version = "swim-annotation.v2" 且 `verified = false`
- **THEN** metrics 层 MUST NOT 使用 `frame / video_fps` 推导时间，所有时间类指标 blocked

#### Scenario: v1 continues to use frame/fps
- **WHEN** schema_version = "swim-annotation.v1"
- **THEN** metrics 层继续使用 `frame / fps` 兼容计算，不受 v2 规则影响

### Requirement: Frame mapping stored in NormalizedAnnotation
系统 SHALL 在 NormalizedAnnotation 的 `annotation_metadata` 中保存 `frame_mapping` 结构。

#### Scenario: Save frame mapping on parse
- **WHEN** CVAT XML 解析完成且 frame mapping 可用
- **THEN** `annotation_metadata.frame_mapping` MUST 包含 `{mode, verified, source_frame_offset, source_frame_stride, video_fps}`

#### Scenario: No mapping available
- **WHEN** 无法确定 frame mapping
- **THEN** `frame_mapping.mode` MUST 为 `"unknown"`，`verified` 为 `false`

### Requirement: ParseAnnotationOptions enables user input
parse endpoint SHALL 接受可选的请求体 `ParseAnnotationOptions`，包含 `frame_mapping_override` 和 `analysis_ranges`。

#### Scenario: Parse with frame_mapping_override
- **WHEN** 用户在 parse 请求中提供 `frame_mapping_override = { mode: "affine", source_frame_offset: 32, source_frame_stride: 1, confirmed: true }`
- **THEN** `FrameMappingResolver` MUST 使用该配置优先于自动推断

#### Scenario: Parse with analysis_ranges
- **WHEN** 用户在 parse 请求中提供 `analysis_ranges = [{ start_annotation_frame: 0, end_annotation_frame: 55 }]`
- **THEN** 系统 MUST 存储该范围，quality checker 基于此计算覆盖率

### Requirement: annotation_fps is derived, not authoritative
`annotation_fps` SHALL 作为派生摘要字段，从相邻帧 `timestamp_sec` 间隔的中位数计算，不作为时间计算输入。

#### Scenario: annotation_fps derived from median interval
- **WHEN** NormalizedAnnotation 的 keypoint_frames 具有完整的 `timestamp_sec`
- **THEN** 系统 MUST 计算相邻帧 `timestamp_sec` 差值的倒数，取中位数作为 `annotation_fps`
