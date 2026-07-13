# Design: Add side-view technical metrics calculation

## 1. 设计约束（本 change 的硬性规则）

1. Metrics are factual measurements, not diagnostics. 只输出测量值，不输出诊断句子。
2. Side-view metrics are computed from `NormalizedAnnotation` only. 引擎只读取 annotation，不修改它。
3. Metrics persistence uses `annotation_metrics`, not `analysis_results`. 不复用模型服务结果表。
4. `calculate-metrics` endpoint is the primary entrypoint, not `AnalysisTask`. 不接入 `run_analysis_task` / `ModelServiceClient` 管线。
5. `reference_lines` / `distance_markers` / `swim_direction` 是富指标（髋深、速度、划幅、相位）的前提；缺则对应指标降级为 null + warning。
6. `phase_metrics` 仅在 `distance_markers` 存在时生成；否则 `phase_metrics = []` 并记 `no_phase_context` warning。
7. `point.visibility` 控制指标质量与权重：occluded 降权、missing 跳过、visible 全权。
8. `event.side` 控制单侧划水周期计算：用 `side` 过滤出单侧 `hand_entry` 严格算 `stroke_rate_spm = 60 / 单侧周期`。
9. 缺字段不崩溃：以 null + quality warning 降级，而非抛未捕获异常。
10. Report score 兼容性推迟到 Change #6 的 report data adapter；本 change 不保证兼容 legacy `body_line_score` 等分数键。

## 2. 架构与数据流

```
normalized_annotations (扩展: reference_lines / distance_markers / swim_direction)
        │
        ▼
POST /api/normalized-annotations/{id}/calculate-metrics?persist=true
        │
        ▼
side_view_metrics_engine.calculate(annotation, view_type)
        │
        ├─ geometry        (点/向量/角度/距离/投影，读 .x/.y，门控 visibility)
        ├─ quality         (event.side / point.visibility 感知，缺字段降级)
        ├─ body_metrics    (body_angle / hip_depth / streamline_index)
        ├─ upper_limb      (entry_angle / front_reach / elbow_angle / forearm_drop / catch·pull duration)
        ├─ leg_metrics     (knee / hip / ankle angle, kick_frequency)
        ├─ rhythm_metrics  (cycle / stroke_rate / stroke_length / speed / swolf)
        └─ phase_metrics   ★仅当 distance_markers 存在
        │
        ▼
SideViewMetrics (schema_version = "swim-side-metrics.v1")
        │
        ▼
annotation_metrics  (持久化, 主键 normalized_annotation_id + calculator + version 唯一)

后续（不在本 change）:
annotation_metrics → Change #5 rule-based diagnostics → annotation_diagnostics
annotation_metrics + diagnostics + visual_assets → Change #6 ReportData → HTML/PDF/frontend
```

## 3. annotation_metrics 表（P1，独立新表）

```sql
CREATE TABLE annotation_metrics (
    id BIGSERIAL PRIMARY KEY,

    normalized_annotation_id BIGINT NOT NULL
        REFERENCES normalized_annotations(id) ON DELETE CASCADE,

    session_video_id BIGINT,          -- 冗余快照, 跟随 normalized_annotation.session_video_id
    schema_version VARCHAR(50) NOT NULL DEFAULT 'swim-side-metrics.v1',
    camera_view VARCHAR(50) NOT NULL DEFAULT 'side',

    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    quality JSONB NOT NULL DEFAULT '{}'::jsonb,

    calculator VARCHAR(100) NOT NULL DEFAULT 'side_view_metrics',
    calculator_version VARCHAR(50) NOT NULL DEFAULT '0.1.0',

    created_by BIGINT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(normalized_annotation_id, calculator, calculator_version)
);
```

注意：以 `normalized_annotation_id` 为主路径，`session_video_id` 仅作冗余快照；不引入 `session_id + video_file_id` 作为主路径，跟随现有 `normalized_annotations` 以 `session_video_id` 为归属的约定。

## 4. Endpoint 契约

```
POST /api/normalized-annotations/{id}/calculate-metrics?persist=true
```
- `persist=true`：计算并写入 `annotation_metrics`，返回 `annotation_metric_id`
- `persist=false`（默认）：仅计算返回，不落库
- 返回：
```json
{
  "annotation_metric_id": 901,
  "normalized_annotation_id": 401,
  "schema_version": "swim-side-metrics.v1",
  "camera_view": "side",
  "metrics": {},
  "quality": { "level": "good", "warnings": [] }
}
```

```
GET /api/normalized-annotations/{id}/metrics
GET /api/annotation-metrics/{id}
```
- 前者方便前端从标注页读取；后者方便后续诊断模块按 metric id 直接引用
- 两个都做；返回最新一条（或指定 `calculator_version`）`annotation_metrics` 记录

## 5. 指标定义摘要（MVP 12 核心 + 延期项）

### A. 姿态结构
- `body_angle_deg`：shoulder→ankle 连线与水平夹角（image y 轴向下，取 abs）。另可算 shoulder_hip / hip_ankle 作为辅助。
- `hip_depth_cm`：需 `reference_lines.waterline`；`(hip.y - waterline_y@hip.x) / ppm * 100`；无 waterline → null + warning。
- `streamline_index`：0–100 内部复合子分，`100 - body_angle_penalty - hip_depth_penalty - line_deviation_penalty`（MVP 简化规则，后续教练校准）。
- `body_line_deviation_cm`：**延期到 v2**（需拟合参考线，定义模糊）。

### B. 上肢
- `entry_angle_deg`：`hand_entry` 帧 shoulder→wrist 与水平夹角（辅助指标，非强诊断核心）。
- `front_reach_distance_cm`：`abs(wrist.x - shoulder.x) / ppm * 100`；正负由 `swim_direction` 消歧。
- `elbow_angle_deg`：shoulder-elbow-wrist 三点夹角（关键指标）。
- `forearm_drop_angle_deg`：elbow→wrist 与水平夹角。
- `catch_duration_sec` / `pull_duration_sec`：`catch_start`→`pull_end` 等事件的 `time_sec` 差值（低成本，纳入 MVP）。

### C. 腿部
- `knee_angle_deg`：hip-knee-ankle 三点夹角（关键指标）。
- `hip_angle_deg`：shoulder-hip-knee 夹角（已有三点，近乎免费，纳入 MVP）。
- `ankle_extension_angle_deg`：knee-ankle-? 夹角（纳入 MVP）。
- `kick_frequency_hz`：有 `kick_downbeat` 事件时 `kick_count / duration_sec`；无则 null。
- `kick_amplitude_cm`：**延期到 v2**（需踝部轨迹密度，标注稀疏时不准）。

### D. 节奏与效率
- `stroke_cycle_duration_sec`：单侧 `hand_entry` 相邻间隔 `/ fps`（用 `event.side` 过滤）。
- `stroke_rate_spm`：`60 / 单侧周期`；定义固定为"单侧完整划水次数/分钟"，写进指标文档。
- `stroke_count`：周期内单侧划水计数。
- `stroke_length_m`：优先级1 = `distance_markers` 的 `distance_delta / stroke_count`；否则 `average_speed_mps / (stroke_rate_spm / 60)` 估算。
- `average_speed_mps`：基于 `distance_markers` 推导；无则 null。
- `swolf`：`time_sec + stroke_count`，保留 `distance_m` 上下文（如 `{"value":81.3,"distance_m":200,"definition":"time_sec+stroke_count"}`）。
- `technical_stability_score`：整体复合分；MVP 可先等于 `streamline_index` 并留扩展位，与 `streamline_index` 明确区分（前者整体、后者身体流线子分）。

### phase_metrics（条件生成）
- 仅当 `distance_markers` 存在：按瞬时速度阈值分 `low_speed` / `middle_speed` / `high_speed`，每相给 `representative_frame` 与一组核心指标。
- 无 `distance_markers`：`phase_metrics = []` + `no_phase_context` warning。

## 6. 质量等级

- `good`：核心指标（角度、划频、划幅、速度）均可计算。
- `warning`：部分指标缺失（如缺 waterline → hip_depth 降级；缺 distance_markers → phase_metrics 空），仍可读。
- `error`：缺 `fps`、缺核心关键点（shoulder/elbow/wrist/hip/knee/ankle）、或 keypoint_frames 不足 3 帧 → 无法计算核心指标。
- 最低必需项：`fps` + `scale.pixels_per_meter` + ≥3 帧关键点（六点齐全）+ ≥1 个 `hand_entry` 或 start/end 事件。

## 7. 与 analysis_results 解耦说明

`analysis_results` 当前语义为"模型服务分析结果"（`run_analysis_task` → `ModelServiceClient.analyze(videos)`）。Change #4 是本地基于 `NormalizedAnnotation` 的确定性计算，来源、执行方式、结果 schema 均不同。强行合并需为复用 `analysis_results` 硬造 `AnalysisTask` 行，且会使 Change #5/#6 再拆回。故采用 P1：独立 `annotation_metrics` 表，Change #4 不碰 `analysis_tasks` / `analysis_results` / `model_service` 管线。

## 8. 实现约定（对接真实代码）

- 关键点读取：`points` 是 `dict[str, KeypointPoint]`，每个点含 `.x/.y/.confidence/.visibility`，geometry 必须读 `.x/.y`（不是 `[x,y]` 列表）。
- `event.side`（`left/right/both/unknown`）用于单侧周期计算。
- `view_type` 从 `session_videos.view_type` 推导（Change #2 spec 规定 `normalized_annotations` 不冗余存 `camera_view`）；引擎入口接收 `view_type` 参数而非 `annotation.camera_view`。
- `manual_tags` 为 `list[ManualTag{code,label,severity,phase}]` 结构化对象（非字符串）；Change #4 仅透传，不用于计算，Change #5 读取其 `code/label/severity`。
- Pydantic schema 放 `app/schemas/metrics.py`（贴合现有 `app/schemas/*` 约定），逻辑放 `app/services/metrics/`。
