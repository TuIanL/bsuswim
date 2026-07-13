## 1. Metrics Output Schema

- [x] 1.1 新增 `backend/app/schemas/metrics.py`，定义 `MetricValue`（key/label/value/unit/source/quality）与 `SideViewMetrics`（`schema_version="swim-side-metrics.v1"`、`summary`/`time_series`/`cycles`/`phase_metrics`/`quality`）
- [x] 1.2 `value` 允许 `float | int | None`，空指标不报错，`quality` 含 `confidence` / `missing`
- [x] 1.3 更新 `schemas/__init__.py` 导出新 schema

## 2. Amend normalized annotation schema

- [x] 2.1 在 `NormalizedAnnotationCreate` / `NormalizedAnnotationRead` 新增 `reference_lines`、`distance_markers`、`swim_direction` 字段（`reference_lines` 含 `waterline`；`distance_markers` 为 `[{frame,time_sec,distance_m,source}]`；`swim_direction` 枚举或自由字符串）
- [x] 2.2 在 `NormalizedAnnotation` 模型新增对应 JSONB 列
- [x] 2.3 更新 Change #2 的 `normalized-annotation-schema` spec，增补上述三字段的 Requirement 与 Scenario

## 3. Migration: annotation fields + annotation_metrics

- [x] 3.1 新增 alembic 迁移：为 `normalized_annotations` 加 `reference_lines` / `distance_markers` / `swim_direction` 三列
- [x] 3.2 新增 alembic 迁移：创建 `annotation_metrics` 表（见 design.md DDL），含 `normalized_annotation_id` 外键与唯一约束 `(normalized_annotation_id, calculator, calculator_version)`
- [x] 3.3 新增 `annotation_metrics` ORM 模型 `AnnotationMetric`（`backend/app/models/annotation_metric.py`）与 `models/__init__.py` 导出

## 4. Geometry Utilities

- [x] 4.1 新增 `backend/app/services/metrics/geometry.py`：`distance_px` / `distance_cm(p1,p2,ppm)` / `angle_between_points(a,b,c)` / `angle_to_horizontal(p1,p2)` / `project_point_to_line` / `vertical_distance_to_line`
- [x] 4.2 读取关键点 `.x/.y`（非 `[x,y]` 列表）；`visibility=missing` 的点返回 None 供调用方跳过
- [x] 4.3 三点角度能正确算 90/120/180；水平夹角正确处理左右方向；缺点返回 None

## 5. Metric Quality Validator

- [x] 5.1 新增 `backend/app/services/metrics/quality.py`：检查 `fps` / `scale.pixels_per_meter` / `camera_view==side` / 六核心关键点 / `hand_entry` 事件 / `waterline` / `distance_markers`
- [x] 5.2 利用 `event.side` 与 `point.visibility` 做门控：occluded 降权、missing 跳过
- [x] 5.3 输出 `level`（good/warning/error）+ `computed_metric_count` / `skipped_metric_count` + `warnings[]`（含 `code`/`message`）
- [x] 5.4 缺 waterline → `missing_waterline` warning（hip_depth 降级）；缺 distance_markers → `no_phase_context` warning（phase_metrics 空）

## 6. Body Position Metrics

- [x] 6.1 新增 `body_metrics.py`：`calculate_body_position_metrics(annotation)` 输出 `body_angle_deg`（shoulder→ankle，取 abs）、`hip_depth_cm`（需 waterline）、`streamline_index`
- [x] 6.2 同时输出 `time_series.body_angle_deg`（每帧 angle + frame + time_sec）
- [x] 6.3 无 waterline 时 `hip_depth_cm` 为 null + warning，不阻塞其余指标

## 7. Upper-limb Metrics

- [x] 7.1 新增 `upper_limb_metrics.py`：`entry_angle_deg`（hand_entry 帧）、`front_reach_distance_cm`（swim_direction 消歧）、`elbow_angle_deg`、`forearm_drop_angle_deg`
- [x] 7.2 `catch_duration_sec` / `pull_duration_sec` 由事件 `time_sec` 差值计算
- [x] 7.3 缺事件时从全部 keypoint_frames 求平均，quality 标 `estimated`

## 8. Leg Technique Metrics

- [x] 8.1 新增 `leg_metrics.py`：`knee_angle_deg`（hip-knee-ankle）、`hip_angle_deg`、`ankle_extension_angle_deg`
- [x] 8.2 `kick_frequency_hz`：有 `kick_downbeat` 事件时计算；无则 null 不阻塞
- [x] 8.3 `kick_amplitude_cm` 标记为 v2 延期，不在 MVP 实现

## 9. Rhythm & Efficiency Metrics

- [x] 9.1 新增 `rhythm_metrics.py`：`stroke_cycle_duration_sec`（单侧 hand_entry 间隔/fps，用 `event.side` 过滤）、`stroke_rate_spm`、`stroke_count`
- [x] 9.2 `stroke_length_m`：优先级1 用 `distance_markers` 的 `distance_delta/stroke_count`；否则 `average_speed_mps/(stroke_rate_spm/60)` 估算
- [x] 9.3 `average_speed_mps` 基于 `distance_markers` 推导；无则 null
- [x] 9.4 `swolf`：`time_sec + stroke_count`，保留 `distance_m` 上下文
- [x] 9.5 输出 `cycles[]`（cycle_index/start_frame/end_frame/duration_sec/events）

## 10. Engine Entry & phase_metrics

- [x] 10.1 新增 `engine.py`：`calculate_side_view_metrics(annotation, view_type) -> SideViewMetrics`，编排 body/upper/leg/rhythm 四组 + quality
- [x] 10.2 `phase_metrics`：仅当 `distance_markers` 存在时按瞬时速度阈值分 low/middle/high，给 `representative_frame` 与核心指标；否则空 + warning
- [x] 10.3 `technical_stability_score` 作为整体复合分（MVP 可先等于 `streamline_index`），与 `streamline_index` 明确区分

## 11. Service & API Endpoint

- [x] 11.1 新增 service：`calculate_and_persist(annotation_id, persist)` 写入 `annotation_metrics`（唯一约束 upsert）
- [x] 11.2 `POST /api/normalized-annotations/{id}/calculate-metrics?persist=` 调用引擎并返回 `annotation_metric_id` + metrics + quality
- [x] 11.3 `GET /api/normalized-annotations/{id}/metrics` 与 `GET /api/annotation-metrics/{id}` 读取最新 `annotation_metrics`
- [x] 11.4 非 side 视角返回 422（UnsupportedCameraView）；缺 fps/关键点返回 422 并附 quality

## 12. Fixtures & Tests

- [x] 12.1 fixtures：`normalized_annotation_side_minimal.json`、`_missing_waterline.json`、`_full_cycle.json`
- [x] 12.2 单测：身体角度/肘角/膝角/划频计算正确
- [x] 12.3 单测：缺 waterline 不报错（hip_depth 降级）；缺 distance_markers 时 phase_metrics 空
- [x] 12.4 单测：缺 fps / 缺核心关键点返回可控 error，不崩
- [x] 12.5 API 集成测试：persist=true 写入 `annotation_metrics`；GET 能读回

## 13. Metric Definitions Doc

- [x] 13.1 新增 `docs/side_view_metrics.md`：每个指标的名称/中文名/公式/所需关键点/所需事件/单位/缺失处理/是否进 MVP 报告
- [x] 13.2 明确 `stroke_rate_spm` 定义（单侧完整划水次数/分钟）、`swim_direction` 用途、`event.side` 用法、`visibility` 门控规则

## 14. Spec Artifacts

- [x] 14.1 新建 capability spec `side-view-metrics/spec.md`（Requirements：输出 schema / 计算端点 / 读取端点 / 持久化 annotation_metrics / 质量等级 / phase gating / visibility 门控 / side 周期 / 缺字段降级 / report 兼容推迟）
- [x] 14.2 amend `normalized-annotation-schema` spec：reference_lines / distance_markers / swim_direction 三字段 Requirement
