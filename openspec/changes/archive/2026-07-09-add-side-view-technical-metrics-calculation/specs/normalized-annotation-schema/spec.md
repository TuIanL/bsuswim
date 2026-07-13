# normalized-annotation-schema Amendment (side-view metric context)

## Purpose
本文件为 Change #2 `normalized-annotation-schema` 的增量修订，新增支撑 side-view metrics 计算的三个字段：`reference_lines`（含 `waterline`）、`distance_markers`、`swim_direction`。这些字段使 `hip_depth_cm`、速度、划幅、相位对比等富指标可计算，否则 Change #4 只能产出角度类指标。

## ADDED Requirements

### Requirement: reference_lines carries waterline
系统 SHALL 在 `normalized_annotations` 支持 `reference_lines` 字段（JSONB），至少含 `waterline` 子结构 `{points: [[x1,y1],[x2,y2]], confidence, source}`。

#### Scenario: Create with waterline
- **WHEN** 创建 normalized annotation 并在 `reference_lines.waterline` 提供两点
- **THEN** 系统 MUST 存储该水面线，metrics 引擎可据此计算 `hip_depth_cm`

#### Scenario: Absent waterline degrades hip_depth
- **WHEN** annotation 不含 `reference_lines.waterline`
- **THEN** quality checker MUST 允许创建成功，但 metrics 层 MUST 将 `hip_depth_cm` 置为 null 并记 `missing_waterline` warning

### Requirement: distance_markers for speed and stroke length
系统 SHALL 支持 `distance_markers` 字段（JSONB 数组），元素含 `frame`、`time_sec`、`distance_m`、`source`，用于在 clips 内推导瞬时速度、划幅与相位分段。

#### Scenario: Create with distance_markers
- **WHEN** 创建 normalized annotation 并提供 `distance_markers`
- **THEN** 系统 MUST 存储，metrics 层可据其计算 `average_speed_mps`、`stroke_length_m`（优先级1）与 `phase_metrics`

#### Scenario: Absent distance_markers
- **WHEN** annotation 不含 `distance_markers`
- **THEN** `average_speed_mps` / `stroke_length_m`（距离版）/ `phase_metrics` MUST 降级或为空，并记 `no_phase_context` / 相应 warning，不报错

### Requirement: swim_direction for front reach sign
系统 SHALL 支持 `swim_direction` 字段（如 `left_to_right` / `right_to_left`），用于消除 `front_reach_distance_cm` 等方向上的正负歧义。

#### Scenario: Create with swim_direction
- **WHEN** 创建 normalized annotation 并指定 `swim_direction`
- **THEN** 系统 MUST 存储，metrics 层据其确定前伸距离的符号方向

#### Scenario: Absent swim_direction
- **WHEN** annotation 不含 `swim_direction`
- **THEN** 系统 MUST 允许创建；`front_reach_distance_cm` 以绝对值计算，quality 标注方向未消歧（不阻塞）

### Requirement: Schema migration adds three fields
系统 SHALL 通过 alembic 迁移为 `normalized_annotations` 表新增 `reference_lines`、`distance_markers`、`swim_direction` 三列（JSONB / 字符串），不破坏现有数据。

#### Scenario: Migration applies cleanly
- **WHEN** 执行新增迁移
- **THEN** 现有 `normalized_annotations` 记录的这三个字段 MUST 默认为空/Null，旧记录仍可正常读取

### Requirement: Quality checker aware of new fields
quality checker SHALL 在缺 `waterline` 时将 `hip_depth_cm` 相关模块标记为不可用（warning 级），不因新字段缺失而整体 error。

#### Scenario: Waterline missing is warning not error
- **WHEN** fps、scale、关键点、事件均完整但缺 `reference_lines.waterline`
- **THEN** quality.level MUST 为 `warning`，`usable_modules` 排除依赖 waterline 的指标，`hip_depth_cm` 降级
