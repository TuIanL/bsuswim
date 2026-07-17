## ADDED Requirements

### Requirement: Manifest-based explicit mapping verifies by four conditions

`_resolve_explicit()` SHALL 在四项条件全部满足时才返回 `verified=True`：
1. entries 非空
2. entry 的 `annotation_frame` 无重复
3. 每个 `required_annotation_frames` 中的帧都有对应 entry
4. 每条 entry 都包含 `source_video_frame` 或 `timestamp_sec`

`FrameMappingResolver.resolve()` SHALL 接收 `required_annotation_frames: set[int]` 参数，值来自 `[f.annotation_frame for f in raw_keypoint_frames]`。

#### Scenario: All four conditions met
- **WHEN** entries 非空、annotation_frame 唯一、全部所需帧有 entry、每条 entry 均含 `source_video_frame`
- **THEN** 系统 MUST 返回 `mode=explicit, verified=true`

#### Scenario: Incomplete coverage (missing required frame)
- **WHEN** 某 required_annotation_frame 在 manifest 中没有对应 entry
- **THEN** 系统 MUST 返回 `mode=explicit, verified=false, verification_reason="incomplete_manifest_coverage"`

#### Scenario: Duplicate annotation_frame
- **WHEN** manifest 中存在重复的 `annotation_frame`
- **THEN** 系统 MUST 返回 `mode=explicit, verified=false, verification_reason="duplicate_annotation_frame"`

#### Scenario: Only filenames available
- **WHEN** companion JSON 中每条 entry 仅有 `image_name`，无 `source_video_frame` 或 `timestamp_sec`
- **THEN** 系统 MUST 尝试文件名数字提取和 affine 验证
- **AND** 若成功，MUST 返回 `mode=affine, verified=false, verification_reason="inferred_from_filename_sequence"`
- **AND** 若失败，MUST 返回 `mode=unknown, verified=false`

#### Scenario: Partial time evidence
- **WHEN** 部分 entry 含 `source_video_frame`，部分仅含 `image_name`
- **THEN** 系统 MUST 返回 `mode=explicit, verified=false, verification_reason="partial_extraction_manifest"`

### Requirement: Filename number extraction uses final numeric token

系统 SHALL 从伴 JSON image 的 `file_name` 中、扩展名前提取最后一段数字序列，路径中的数字不被提取。

#### Scenario: Extract final numeric token
- **WHEN** `file_name = "vlc/scene00032.jpg"`
- **THEN** 提取结果 MUST 为 `32`

#### Scenario: No numeric token found
- **WHEN** `file_name = "scene_final.jpg"`
- **THEN** 提取 MUST 返回空，无法用于推断

### Requirement: Affine inference requires constant stride

系统 SHALL 验证文件名序列严格满足恒定 offset + stride，拒绝任何不满足的序列。

#### Scenario: Consecutive sequence
- **WHEN** filenames 提取为 `[32, 33, 34]`，annotation_frames 为 `[0, 1, 2]`
- **THEN** 系统 MUST 计算 `offset=32, stride=1`，返回 `mode=affine, verified=false`

#### Scenario: Every-other-frame sequence
- **WHEN** filenames 提取为 `[32, 34, 36]`，annotation_frames 为 `[0, 1, 2]`
- **THEN** 系统 MUST 计算 `offset=32, stride=2`，返回 `mode=affine, verified=false`

#### Scenario: Non-constant stride rejected
- **WHEN** filenames 提取为 `[32, 33, 35]`，annotation_frames 为 `[0, 1, 2]`
- **THEN** 系统 MUST 返回 `mode=unknown, verification_reason="filename_sequence_not_affine"`

#### Scenario: Single entry insufficient
- **WHEN** 仅有一条 filename entry
- **THEN** 系统 MUST 返回 `mode=unknown, verification_reason="insufficient_filename_sequence"`

#### Scenario: Duplicate annotation_frame rejected
- **WHEN** 存在重复的 `annotation_frame`
- **THEN** 系统 MUST 返回 `mode=unknown, verification_reason="duplicate_annotation_frame"`

### Requirement: Two-path timestamp derivation

系统 SHALL 按来源采用两条路径生成 timestamp_sec：

**路径 A（manifest 直接提供）**：manifest entry 中已包含 `timestamp_sec` 且 mapping verified 时直接保留，不依赖 fps_verified。

**路径 B（source_video_frame 派生）**：仅从 `source_video_frame` 推导时，必须同时满足 `mapping_verified` 和 `fps_verified`。

#### Scenario: Direct timestamp from manifest preserved
- **WHEN** manifest entry 包含 `timestamp_sec` 且 `mapping.verified=true`
- **THEN** normalizer MUST 直接保留该时间戳，不检查 fps_verified

#### Scenario: Direct timestamp but mapping unverified
- **WHEN** manifest entry 包含 `timestamp_sec` 但 `mapping.verified=false`
- **THEN** normalizer MUST 将 `timestamp_sec` 设为 None

#### Scenario: Derived timestamp needs both verified
- **WHEN** manifest 仅提供 `source_video_frame`，且 `mapping.verified=true`、`fps_verified=true`
- **THEN** normalizer MUST 通过 `source_video_frame / fps` 推导 `timestamp_sec`

#### Scenario: Derived timestamp blocked by unverified FPS
- **WHEN** manifest 仅提供 `source_video_frame`，`mapping.verified=true` 但 `fps_verified=false`
- **THEN** normalizer MUST 不推导 `timestamp_sec`，设为 None

### Requirement: Resolver does not derive timestamps

`FrameMappingResolver` SHALL 只解析、验证和保存 manifest 中原本存在的时间证据，不得自行使用 FPS 推导 timestamp_sec。

#### Scenario: Resolver passes through manifest timestamp_sec
- **WHEN** manifest entry 包含 `timestamp_sec`
- **THEN** resolver MUST 在 `FrameMappingEntry.timestamp_sec` 中保留该值

#### Scenario: Resolver does not compute from source_video_frame
- **WHEN** manifest entry 包含 `source_video_frame` 但不含 `timestamp_sec`
- **THEN** resolver MUST 将 `FrameMappingEntry.timestamp_sec` 设为 None
- **AND** resolver MUST NOT 使用 `source_video_frame / video_fps` 计算 timestamp

### Requirement: FPS trust metadata recorded

系统 SHALL 在 `annotation_metadata.video` 中记录 `fps_source` 和 `fps_verified`。

#### Scenario: FPS from session_video
- **WHEN** `session_video.fps` 可用
- **THEN** `video.fps_source` MUST 为 `"session_video"`，`video.fps_verified` MUST 为 `true`

#### Scenario: FPS from annotation_file with source evidence
- **WHEN** `session_video.fps` 不可用，`annotation_file.annotation_fps` 可用，且有 metadata 标记 `user_provided`
- **THEN** `video.fps_source` MUST 为 `"annotation_file"`，`video.fps_verified` MUST 为 `true`

#### Scenario: FPS from annotation_file without source evidence
- **WHEN** `annotation_file.annotation_fps` 非空但无来源 metadata
- **THEN** `video.fps_source` MUST 为 `"annotation_file_unverified"`，`video.fps_verified` MUST 为 `false`

#### Scenario: FPS compatibility default
- **WHEN** 无可用 FPS 来源
- **THEN** `video.fps_source` MUST 为 `"compatibility_default"`，`video.fps_verified` MUST 为 `false`

## MODIFIED Requirements

### Requirement: verified requires explicit confirmation or direct time evidence

`frame_mapping.verified` SHALL 仅通过三种途径设为 `true`：用户通过 `ParseAnnotationOptions` 显式确认；`extraction_manifest` 提供逐帧 `source_video_frame` 或 `timestamp_sec`；所有 entry 均含时间证据。

#### Scenario: Filename sequence infers affine but not verified
- **WHEN** 图片文件名连续（如 `scene00032.jpg`、`scene00033.jpg`），无 manifest 且无用户确认
- **THEN** 系统 MUST 推断 `mode = "affine"`，`verified = false`，`verification_reason` 记录 `"inferred_from_filename_sequence"`

#### Scenario: User confirmation sets verified=true
- **WHEN** 用户在 `ParseAnnotationOptions.frame_mapping_override` 中提供 `confirmed = true`
- **THEN** 系统 MUST 将 `verified` 设为 `true`

#### Scenario: Manifest with all source_video_frame sets verified=true
- **WHEN** companion JSON 为每条 entry 提供 `source_video_frame`
- **THEN** 系统 MUST 将 `verified` 设为 `true`

#### Scenario: Manifest with filenames only sets verified=false
- **WHEN** companion JSON 仅提供 `file_name`，无 `source_video_frame` 或 `timestamp_sec`
- **THEN** 系统 MUST 将 `verified` 设为 `false`

### Requirement: Unverified mapping is treated as blocked for time metrics

当 `verified = false` 时，无论 mode 为何，metrics 层 SHALL 将所有时间类指标标记为 blocked。

#### Scenario: Unverified explicit blocks time metrics
- **WHEN** `frame_mapping.mode = "explicit"` 但 `verified = false`
- **THEN** quality checker MUST 添加 `TIME_MAPPING_UNVERIFIED` warning，时间类指标 blocked

#### Scenario: Unverified unknown blocks time metrics
- **WHEN** `frame_mapping.mode = "unknown"` 且 `verified = false`
- **THEN** quality checker MUST 添加 `TIME_MAPPING_UNVERIFIED` warning，时间类指标 blocked
