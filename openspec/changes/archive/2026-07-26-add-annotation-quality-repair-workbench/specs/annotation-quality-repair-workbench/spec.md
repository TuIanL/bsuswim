## ADDED Requirements

### Requirement: Quality issues expose executable repair actions
质量报告中的可修复问题 SHALL 包含稳定的 `suggested_action.type`、展示 label 和必要的 payload；前端 SHALL 能根据 action 打开对应修复步骤。

#### Scenario: Missing scale opens scale repair
- **WHEN** quality issues include `SCALE_INVALID` 或 `SCALE_MISSING`
- **THEN** issue MUST include an action type that opens the scale editor
- **AND** the editor MUST target the selected normalized annotation

#### Scenario: Missing waterline opens waterline repair
- **WHEN** quality issues include `WATERLINE_MISSING`
- **THEN** issue MUST include an action type that opens the waterline editor

### Requirement: Repair workbench uses the bound side video
工作台 SHALL 使用当前 session 绑定的 side video 作为背景，显示当前帧、视频时间和可操作的帧定位控件。

#### Scenario: Video frame is available
- **WHEN** selected annotation has a bound side video that loads successfully
- **THEN** workbench MUST show the video frame and allow previous/next frame and timeline positioning

#### Scenario: Video frame is unavailable
- **WHEN** bound side video cannot load
- **THEN** workbench MUST show an explicit error
- **AND** MUST disable canvas-based scale, waterline and event marking
- **AND** MUST keep non-visual direction and mapping fields editable when possible

### Requirement: User can define a pixel scale
工作台 SHALL 允许用户在视频帧上选择两个参考点并填写真实长度，服务 SHALL 验证长度为正并保存 `scale.reference_points`、`scale.reference_length_m` 和 `scale.pixels_per_meter`。

#### Scenario: Valid scale is saved
- **WHEN** user selects two distinct points and enters a positive reference length in meters
- **THEN** system MUST calculate pixels_per_meter from the pixel distance
- **AND** save the scale in the normalized annotation revision

#### Scenario: Invalid scale is rejected
- **WHEN** the two selected points coincide, coordinates are outside the intrinsic video bounds, or reference length is not positive
- **THEN** system MUST reject the repair
- **AND** MUST leave the current annotation revision unchanged

### Requirement: User can define a waterline
工作台 SHALL 允许用户在视频帧上选择两个点并保存为 `reference_lines.waterline.points` 的原始像素坐标。

#### Scenario: Waterline is saved
- **WHEN** user selects two distinct in-bounds points and confirms the waterline
- **THEN** system MUST save both points in `reference_lines.waterline`
- **AND** subsequent validation MUST no longer report `WATERLINE_MISSING`

#### Scenario: Degenerate waterline is rejected
- **WHEN** waterline contains fewer than two points or non-finite/out-of-bounds coordinates
- **THEN** system MUST reject the repair
- **AND** MUST preserve the previous reference_lines value

### Requirement: User can set swim direction
工作台 SHALL 提供 `left_to_right` 和 `right_to_left` 两个明确选项，并保存所选方向。

#### Scenario: Direction is saved
- **WHEN** user selects a supported swim direction and saves the repair
- **THEN** `NormalizedAnnotation.swim_direction` MUST equal the selected value
- **AND** validation MUST no longer report `SWIM_DIRECTION_UNSET`

### Requirement: User can mark required events on the timeline
工作台 SHALL 支持在选定视频帧上创建事件，至少支持 `hand_entry`，并保存 annotation frame、source video frame when known, and timestamp.

#### Scenario: Two hand entry events are marked
- **WHEN** user marks two distinct `hand_entry` events and saves
- **THEN** normalized annotation MUST contain at least two `hand_entry` events ordered by frame
- **AND** validation MUST no longer report insufficient complete cycles solely because hand_entry is absent

#### Scenario: Duplicate event is submitted
- **WHEN** the same event name, frame and side already exists
- **THEN** service MUST deduplicate it
- **AND** MUST NOT create duplicate cycle boundaries

### Requirement: User can confirm frame mapping
工作台 SHALL 展示 annotation frame 与 source video frame 的映射预览，并支持提交 affine 或 identity mapping；只有显式确认后才可写入 `verified=true`。

#### Scenario: Affine mapping is confirmed
- **WHEN** user confirms mode affine with a valid offset and positive stride
- **THEN** system MUST save `verified=true`
- **AND** MUST save `verification_reason=user_confirmed`
- **AND** time-dependent quality checks MUST use the confirmed mapping

#### Scenario: Mapping is not confirmed
- **WHEN** mapping values are entered but user does not confirm them
- **THEN** system MUST preserve `verified=false`
- **AND** time-dependent metrics MUST remain blocked or unavailable according to existing rules

### Requirement: Repair API preserves revisions and validates expected revision
系统 SHALL 提供质量修复 API，使用 `expected_revision` 防止并发覆盖；成功保存 SHALL 递增 revision、重新运行质量验证并返回最新 quality 和 analysis readiness。

#### Scenario: Repair succeeds against current revision
- **WHEN** `POST /api/normalized-annotations/{id}/quality-repair` carries the current expected_revision and valid repair payload
- **THEN** system MUST persist the allowed repair fields
- **AND** increment annotation revision by one
- **AND** return quality, module readiness, analysis readiness and new revision

#### Scenario: Stale revision is rejected
- **WHEN** expected_revision differs from the current annotation revision
- **THEN** system MUST return a conflict response
- **AND** MUST NOT overwrite the current annotation

### Requirement: Repair is followed by complete re-validation
质量修复保存后 SHALL 使用与 parse/validate 相同的 profile 和 validator，对完整标准化标注重新生成质量报告，而不是只删除已修复的 issue。

#### Scenario: Scale repair changes module readiness
- **WHEN** an annotation missing scale receives a valid scale repair
- **THEN** validation MUST recompute efficiency readiness from the full annotation
- **AND** unrelated issues MUST remain present

#### Scenario: Repair remains insufficient
- **WHEN** repair does not satisfy all prerequisites
- **THEN** response MUST preserve remaining issues and their severity/module assignments
- **AND** analysis submission MUST continue to follow existing gate rules

