# annotation-derivation Specification

## Purpose
定义从标准化 keypoint_frames 推导派生数据的独立层，包括轨迹（trajectories）、身体中心线（作为派生轨迹）和可见性摘要（visibility summary）。Parser 不承担推导职责，派生层由 parse service 同步调用。

## Requirements

### Requirement: Trajectory builder derives from keypoint_frames
`TrajectoryBuilder` SHALL 从标准化 `KeypointFrame[]` 中按关键点名称和时间排序串联，生成 `Trajectory[]`。

#### Scenario: Trajectory built for each keypoint across frames
- **WHEN** 56 个 keypoint_frames 中 `left_wrist` 在连续多帧中为 `visibility="visible"`
- **THEN** `TrajectoryBuilder` MUST 生成一条 `left_wrist` 轨迹，包含按 timestamp_sec 排序的所有坐标样本

#### Scenario: Missing points create trajectory gaps
- **WHEN** 连续帧中某个关键点变为 `visibility="missing"`
- **THEN** 轨迹中该帧不写入坐标样本，形成轨迹缺口，不生成虚假插值点

#### Scenario: Occluded points included with provenance
- **WHEN** 关键点为 `visibility="occluded"`
- **THEN** 轨迹中包含该坐标样本，标记 `visibility="occluded"`，confidence 保持 null（不自动派生）

#### Scenario: Trajectory provenance recorded
- **WHEN** 生成轨迹
- **THEN** Trajectory MUST 包含 `source="derived_from_keypoints"` 和 `builder_version` 字符串

### Requirement: Native trajectories take priority
当关键点存在原生轨迹（来自 CVAT/Kinovea）时，派生层 SHALL 不覆盖原生轨迹。

#### Scenario: Native trajectory preferred over derived
- **WHEN** parser 输出中包含 `native_trajectories`（如来自 Kinovea）
- **THEN** 系统 MUST 以原生轨迹为准，不对同名关键点重新推导

#### Scenario: Partial native trajectories
- **WHEN** 仅部分关键点具有原生轨迹
- **THEN** 系统 MUST 对无原生轨迹的关键点执行推导

### Requirement: Trajectory builder does no interpolation
`TrajectoryBuilder` SHALL 不做线性插值、样条插值、平滑滤波或异常点修正。

#### Scenario: No interpolation between gaps
- **WHEN** 轨迹中存在 `missing` 导致的缺口
- **THEN** 轨迹样本列表 MUST 保持缺口，不插入估算坐标

### Requirement: Body center builder outputs derived trajectories
`BodyCenterBuilder` SHALL 计算身体中心参考点（如 hip_center），以派生轨迹形式输出，不新增独立顶层字段。

#### Scenario: Hip center as derived trajectory
- **WHEN** `BodyCenterBuilder` 完成计算
- **THEN** hip_center MUST 以 `{point_name: "hip_center", source: "derived_from_keypoints", samples: [...]}` 格式输出

#### Scenario: Hip center from both hips visible
- **WHEN** 同一 frame 内 `left_hip` 和 `right_hip` 均可见
- **THEN** `BodyCenterBuilder` MUST 计算 `hip_center = midpoint(left_hip, right_hip)`

#### Scenario: Single hip visible skips frame
- **WHEN** 同一 frame 内仅一侧髋可见
- **THEN** `BodyCenterBuilder` MUST 不为该帧生成 hip_center，不将单侧髋作为髋部中点

#### Scenario: Both hips missing skips frame
- **WHEN** 同一 frame 内左右髋均不可见
- **THEN** `BodyCenterBuilder` MUST 不为该帧生成 hip_center

### Requirement: Confidence is not auto-derived
CVAT 来源的 confidence SHALL 统一为 null，visibility 权重由 quality/metrics 层派生。

#### Scenario: CVAT confidence is null
- **WHEN** CVAT XML parser 生成点数据
- **THEN** `confidence` MUST 为 null

#### Scenario: Observation weight not in derivation
- **WHEN** metrics 层决定是否使用 occluded 点
- **THEN** 该权重 SHOULD 来自 quality 层，不写入原始点数据

### Requirement: Visibility summary aggregates per-frame keypoint coverage
`VisibilitySummary` SHALL 统计每个关键点在分析范围内的可见帧数、遮挡帧数和缺失帧数。

#### Scenario: Summary for left_wrist
- **WHEN** 56 帧中 `left_wrist` visible 50 帧、occluded 4 帧、missing 2 帧
- **THEN** `VisibilitySummary` MUST 报告 `{keypoint: "left_wrist", visible: 50, occluded: 4, missing: 2, coverage: 0.893}`

### Requirement: Derived data builder called synchronously by parse service
`AnnotationDerivedDataBuilder` SHALL 由 `normalized_annotation_service.py` 在 parse 流程中同步调用，不增加用户操作步骤。

#### Scenario: Parse includes derivation
- **WHEN** `POST /api/annotations/{id}/parse` 完成 CVAT XML 解析
- **THEN** 系统 MUST 在保存 NormalizedAnnotation 之前调用 `AnnotationDerivedDataBuilder.build()`

#### Scenario: Derivation failure does not block parse
- **WHEN** 派生层处理失败（如 Builder 内部异常）
- **THEN** 系统 MUST 不阻止 parse 成功，在 `warnings` 中添加 `derivation_failed`，NormalizedAnnotation 其余字段正常保存
