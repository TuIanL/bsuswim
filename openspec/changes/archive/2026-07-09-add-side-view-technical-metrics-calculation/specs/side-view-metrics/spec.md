# side-view-metrics Specification

## Purpose
定义从 `NormalizedAnnotation` 计算侧面视角（`view_type = side`）技术指标的能力。输出固定 schema 的纯事实测量值（身体角度、肘/膝角、划频、划幅、速度、SWOLF 等），持久化到独立的 `annotation_metrics` 表，供 Change #5（规则诊断）与 Change #6（报告装配）直接消费。本能力只产出测量值，不产出诊断结论。

## ADDED Requirements

### Requirement: Metrics output has fixed schema version
系统 SHALL 以 `swim-side-metrics.v1` 作为 side-view metrics 的 `schema_version`，输出结构固定包含 `summary` / `time_series` / `cycles` / `phase_metrics` / `quality` 字段。

#### Scenario: Calculate returns fixed schema
- **WHEN** 调用 `calculate_side_view_metrics(annotation, view_type)` 且输入有效
- **THEN** 系统 MUST 返回含 `schema_version="swim-side-metrics.v1"` 与 `summary`/`time_series`/`cycles`/`phase_metrics`/`quality` 的结构

#### Scenario: Missing metric is null not error
- **WHEN** 某指标因缺字段无法计算（如缺 waterline 的 `hip_depth_cm`）
- **THEN** 系统 MUST 将该指标 `value` 置为 `null` 并在 `quality.warnings` 记录，不得抛未捕获异常

### Requirement: Metrics are factual, not diagnostic
系统 SHALL 仅输出测量值（如 `body_angle_deg=14`），不得输出诊断句子（如"身体位置偏低"）。复合评分（如 `streamline_index`、`technical_stability_score`）仅作为内部数值，不构成结论。

#### Scenario: No diagnostic text in metrics
- **WHEN** `body_angle_deg=14` 被算出
- **THEN** 输出 MUST 仅为数值指标，不含任何"偏低/不足"类文字结论

#### Scenario: Diagnostic responsibility deferred
- **WHEN** Change #5 需要基于 metrics 输出结论
- **THEN** 系统 MUST 由 rule-based diagnostics 读取 `metrics.summary` + `phase_metrics` + `cycles` + `manual_tags` 后生成，不在本能力内

### Requirement: Persistence uses annotation_metrics table
系统 SHALL 将计算结果持久化到独立的 `annotation_metrics` 表（主键 `normalized_annotation_id` + `calculator` + `calculator_version` 唯一约束），不得写入 `analysis_results`。

#### Scenario: Persist writes annotation_metrics
- **WHEN** `POST /api/normalized-annotations/{id}/calculate-metrics?persist=true` 被调用
- **THEN** 系统 MUST 写入或 upsert 一条 `annotation_metrics` 记录，返回 `annotation_metric_id`

#### Scenario: Not coupled to analysis_results
- **WHEN** metrics 被持久化
- **THEN** 系统 MUST NOT 修改 `analysis_tasks` / `analysis_results` 表，也不接入 `ModelServiceClient` 模型服务管线

### Requirement: Calculate endpoint is primary entrypoint
系统 SHALL 提供 `POST /api/normalized-annotations/{id}/calculate-metrics?persist=` 作为指标计算主入口，不通过 `AnalysisTask` 触发。

#### Scenario: Non-side view rejected
- **WHEN** 目标 annotation 的 `view_type != side`
- **THEN** 端点 MUST 返回 422 并附 `UnsupportedCameraView` 说明

#### Scenario: Persist false returns without storage
- **WHEN** `persist=false`
- **THEN** 系统 MUST 计算并返回 metrics + quality，但不写库

### Requirement: Read endpoints for metrics
系统 SHALL 提供 `GET /api/normalized-annotations/{id}/metrics` 与 `GET /api/annotation-metrics/{id}` 读取最新 `annotation_metrics`。

#### Scenario: Read from annotation page
- **WHEN** 前端从标注页请求 metrics
- **THEN** `GET /api/normalized-annotations/{id}/metrics` MUST 返回该 annotation 的最新 metrics（可按 `calculator_version` 指定）

#### Scenario: Read by metric id for diagnostics
- **WHEN** Change #5 按 metric id 引用
- **THEN** `GET /api/annotation-metrics/{id}` MUST 返回对应 `annotation_metrics` 记录

### Requirement: Quality level and degradation
系统 SHALL 输出 `quality.level`（good/warning/error）与 `computed_metric_count` / `skipped_metric_count` / `warnings[]`。

#### Scenario: Missing waterline degrades hip_depth
- **WHEN** annotation 缺 `reference_lines.waterline`
- **THEN** `hip_depth_cm` MUST 为 null，quality.level=warning，warnings 含 `missing_waterline`

#### Scenario: Missing fps or core keypoints is error
- **WHEN** 缺 `fps` 或缺 shoulder/elbow/wrist/hip/knee/ankle 任一核心关键点或 keypoint_frames < 3 帧
- **THEN** quality.level MUST 为 error，核心指标无法计算

### Requirement: phase_metrics gated on distance_markers
系统 SHALL 仅在 annotation 含 `distance_markers` 时生成 `phase_metrics`（按瞬时速度分 low/middle/high）；否则 `phase_metrics=[]` 并记 `no_phase_context` warning。

#### Scenario: distance_markers present
- **WHEN** annotation 含 `distance_markers`
- **THEN** `phase_metrics` MUST 含按速度阈值划分的阶段，各阶段含 `representative_frame` 与核心指标

#### Scenario: distance_markers absent
- **WHEN** annotation 不含 `distance_markers`
- **THEN** `phase_metrics` MUST 为空数组，quality.warnings 含 `no_phase_context`

### Requirement: point.visibility controls weighting
系统 SHALL 依据每个关键点的 `visibility`（`visible`/`occluded`/`estimated`/`missing`）控制指标质量与权重：occluded 降权、missing 跳过。

#### Scenario: Missing point skipped
- **WHEN** 某帧 ankle 的 `visibility=missing`
- **THEN** 该帧涉及 ankle 的指标（如 `knee_angle_deg`）MUST 跳过该帧或降权，不报错

### Requirement: event.side controls single-side stroke cycle
系统 SHALL 依据事件的 `side` 字段过滤出单侧 `hand_entry`，用 `stroke_rate_spm = 60 / 单侧周期` 计算划频。

#### Scenario: Single-side rate computed
- **WHEN** `hand_entry` 事件含 `side=left`/`side=right`
- **THEN** 系统 MUST 仅用单侧事件计算 `stroke_cycle_duration_sec` 与 `stroke_rate_spm`

### Requirement: Report score compatibility deferred
系统 SHALL NOT 为兼容 `report_builder.py` 遗留的 `body_line_score` / `rhythm_score` / `overall_score` 等分数键修改 metrics schema。

#### Scenario: Legacy score keys not guaranteed
- **WHEN** Change #6 装配报告
- **THEN** 兼容桥接 MUST 由 report data adapter 完成，本能力的 metrics schema 不保证包含 legacy 分数键
