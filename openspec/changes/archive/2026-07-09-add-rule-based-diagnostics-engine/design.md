# Change #5 Design: Rule-based Diagnostics Engine

本文件描述 Change #5 的落地点设计。核心修正：原提案假设 `analysis_results.metrics` 已存在且诊断引擎直接读它；现实是 Change #4 把指标落在独立表 `annotation_metrics`（`swim-side-metrics.v1`），side-view 流尚未创建/更新过 `AnalysisResult`。因此本 change 显式补 **adapter 契约层** 与 **analysis_result 接线桥**，否则引擎只是一个接不住真实数据的孤立纯函数。

## 1. 数据流向（修正后）

```
annotation_metrics.metrics                ← Task #4 实际产物 (swim-side-metrics.v1)
  summary / phase_metrics / cycles / quality
        │
        ▼  DiagnosticsMetricsAdapter         ← Change #5 新增（契约层）
        │
  DiagnosticMetricsContext                ← 规则引擎稳定输入
   (body_angle_deg, hip_depth_cm, … swolf_value,
    front_reach_distance_cm, manual_tags, quality_summary, phase_context)
        │
        ▼  RuleBasedDiagnosticsEngine
        │
  DiagnosticItem[] + DiagnosticsSummary + skipped_rule_ids
        │
        ▼  run_diagnostics_for_analysis_result  ← Change #5 接线桥
        │
  analysis_results.diagnostics            ← 新增列（migration）
  analysis_results.raw_result["diagnostics_meta"]
```

规则 YAML **只认** `DiagnosticMetricsContext` 的稳定逻辑键，永不直接绑定 `annotation_metrics.summary` 的内部键（如 `body_angle_deg_avg`）。未来 Task #4 内部键改名或 AI 姿态识别产出另一套 metrics，只需改 adapter。

## 2. DiagnosticsMetricsAdapter 映射（v1）

| Task #4 实际键 | 诊断逻辑键 | 备注 |
| --- | --- | --- |
| `body_angle_deg_avg` | `body_angle_deg` | |
| `hip_depth_cm_avg` | `hip_depth_cm` | 需 `waterline`，缺失则 null |
| `elbow_angle_deg_avg` | `elbow_angle_deg` | |
| `forearm_drop_angle_deg_avg` | `forearm_drop_angle_deg` | |
| `knee_angle_deg_avg` | `knee_angle_deg` | |
| `stroke_rate_spm_avg` | `stroke_rate_spm` | |
| `stroke_length_m_avg` | `stroke_length_m` | |
| `swolf.value` | `swolf_value` | `swolf` 是对象，取其 `value` |
| `front_reach_distance_cm_avg` | `front_reach_distance_cm` | **保持 cm，不做比例**（见 §6） |
| `kick_frequency_hz` | `kick_frequency_hz` | 直通 |
| `phase_metrics[]` | `phase_context` | 保留嵌套，供未来分速度段规则 |
| `manual_tags` (来自 `NormalizedAnnotation`) | `manual_tags` | 直通 |
| `quality` | `quality_summary` | 直通 |

adapter 对未显式映射但未来规则可能用到的键（`entry_angle_deg_avg` / `hip_angle_deg_avg` / `ankle_extension_angle_deg_avg` / `average_speed_mps` / `streamline_index` / `technical_stability_score` / `stroke_cycle_duration_sec_avg` / `stroke_count`）采取**宽松透传**：原样放进 context，仅在映射明确项上做重命名/展平。adapter 同时记录 `missing_or_unsupported_metrics`（如 `swolf` 缺 `value` 时记 `swolf_value`）。

### 2.1 manual_tags 权威来源（避免命中失败 / 标签漂移）

`manual_tags` 的**权威来源是 `NormalizedAnnotation.manual_tags`**；仅当其缺失或为空时，才回退到 `annotation_metrics.metrics.manual_tags`（可能为旧标注残留）。adapter 统一输出 `context.manual_tags`。不这样规定会出现两类问题：

- 标注里有 `manual_tags` 但 `metrics` 表里没有 → 依赖 `manual_tag` 的规则（R004/R006）无法命中；
- `metrics` 表残留旧 `manual_tags` 与最新标注不一致 → 诊断结论基于过期标签。

### 2.2 phase_context 跳过原因细分（对齐 R003）

`phase_metrics` 缺失或不足时，R003 的跳过原因**必须细分**，便于排查速度阶段类判断（身体位置随速度改善、划频代偿划幅下降等都不是平均值能判断的）：

- `missing_metric:phase_context`：`phase_metrics` 整体为空（无 `distance_markers`，无法分阶段）
- `insufficient_metric:phase_context.distance_markers`：有 `phase_metrics` 但速度分桶依赖的 `distance_markers` 缺失/不足
- `insufficient_metric:phase_context.speed_buckets`：分桶数不足（< low/high 两桶）

## 3. 规则注册表 schema（统一结构化 condition）

`rules/side_freestyle_v1.yaml`：

```yaml
schema_version: swim-diagnostics-rules.v1
stroke: freestyle
camera_view: side
rules:
  - id: R001
    code: low_body_position
    category: body_position
    status: active                # active | dormant
    required_metrics: [body_angle_deg]
    enabled: true
    condition:
      all:
        - metric: body_angle_deg
          op: ">="
          value: 12
    severity:                      # 仅结构化 condition，不支持字符串表达式
      high:
        any:
          - metric: body_angle_deg
            op: ">="
            value: 14
      medium:
        any:
          - metric: body_angle_deg
            op: ">="
            value: 12
    priority_base: 80
    evidence_template: "身体与水平面夹角为 {body_angle_deg}°，提示身体位置偏低。"
    reason_template: "身体未能保持接近水平的流线型姿态，可能增加迎水阻力。"
    suggestion_template: "加强核心控制、髋部支撑与低速阶段身体稳定训练。"
    metric_refs: [body_angle_deg]
    recommendation_tags: [core_control, hip_support, streamline]
    section_key: body_position
```

要点：
- `status: active | dormant`。dormant 规则**永远跳过**，记入 `skipped_rule_ids`（`reason: "dormant"`）。
- `required_metrics`：active 规则若任一必需键在 context 缺失 → 跳过，记 `skipped_rule_ids`（`reason: "missing_metric:<keys>"`）。

> **R003 定位说明**：R003（`body_position_improves_with_speed`）在 §3.4 列表中被归入
> “dormant 组”，但其 `required_metrics` 含特殊 token `phase_context`。实现上 R003 为
> **active + phase-gated**：当 `phase_context` 缺失/不足时按 §2.2 细分原因跳过
> （`missing_metric:phase_context` 等），从而精确匹配 §9 验收样例。其余真正
> `status: dormant` 的规则仅 R005（前伸距离需人体尺度归一化）。R007/R010/R011 则为
> active 但因缺必需指标而跳过。这种划分使“跳过的 5 条”与 §9 完全一致。
- `severity` 只接受结构化 `all` / `any` 的 `condition`（含 `metric` / `op` / `value`）。**不支持字符串表达式**（如 `"swolf > 90 or efficiency_score < 60"`），避免解析/安全坑。
- `op` 集合：`>=` `>` `<` `<=` `==` `!=`。`value_from` / `metric_delta` 不在 v1（分速度段 delta 规则 R011 走 dormant）。

## 4. 评估器语义

- 条件评估只走结构化 `all` / `any`；`evaluator.py` 不实现任何表达式求值器。
- 规则 `required_metrics` 缺失 → 整条跳过（不是错误），进 `skipped_rule_ids`。
- severity 解析中若某分支引用的 metric 在 context 缺失 → **跳过该分支**，不使整条规则失败；缺失分支记入 `partial_evaluation_warnings`（随 diagnostics 返回，便于排查）。这保证 R012 在 `efficiency_score` 缺失时仍能用 `swolf_value` 判级。
- `manual_tag` 命中：条件支持 `any` 内含 `manual_tag: <tag>`，与 metric 条件并列。

## 5. 优先级与去重

- `SEVERITY_WEIGHT = {critical:100, high:80, medium:60, low:40, info:20}`
- `CATEGORY_WEIGHT = {body_position:12, catch_pull:15, arm_entry:10, leg_kick:8, efficiency:14}`
- `priority_score = severity_weight + category_weight + evidence_bonus + manual_tag_bonus + multi_metric_bonus`
- 输出 `priority = 1,2,3...`（排序后），后台保留 `priority_score`。
- 去重/合并：`diagnostic_groups` 定义相关 code（如 `upper_limb_propulsion: primary=insufficient_high_elbow_catch, related=[insufficient_catch_area, low_propulsive_efficiency]`），策略 `keep_primary_attach_related_evidence`。v1 实际多为 primary + 部分 related（因 R007/R008 部分休眠），合并后更像教练写的而非机器罗列。

### 5.1 R006 与 R008 合并（验收硬性要求）

当 R006（高肘抱水不足）与 R008（上肢推进效率不足，基于 `stroke_length_m`）**同时命中**时，最终 coach-facing diagnostics **必须合并为一个主问题**，R008 的证据作为 related evidence 附加到 R006，而非并列两条。否则报告会出现"高肘抱水不足 / 上肢推进效率不足 / 单次划幅不足"的机器罗列感。

合并后预期输出（单一 `DiagnosticItem`）：

```json
{
  "code": "insufficient_high_elbow_catch",
  "title": "高肘抱水不足，影响上肢推进效率",
  "severity": "high",
  "evidence": "抱水阶段肘关节角度 154°，同时单次划幅偏低（1.06 m）。",
  "reason": "前臂未能形成稳定有效迎水面，导致单次推进距离不足。",
  "suggestion": "进行高肘抱水专项、单臂划水、Paddle 抓水与推水衔接训练。",
  "related_diagnostics": [
    { "code": "low_propulsive_efficiency", "evidence": "stroke_length_m=1.06" }
  ]
}
```

验收标准须明确：R006+R008 同命中时，最终 diagnostics 列表里**不应出现两条并列的上肢推进问题**。

## 6. `front_reach_ratio` 决策

v1 **不使用比例**。R005 改用 `front_reach_distance_cm`（cm），但标记为 **dormant**：前伸/划幅类指标最好用人体尺度（身高、臂长、肩峰至指尖长度）或真实标尺归一化后再给固定 cm 阈值，否则阈值无个体化依据。adapter 已暴露 `front_reach_distance_cm`，但未启用基于它的阈值诊断。

## 7. analysis_result 接线桥

`run_diagnostics_for_analysis_result(db, analysis_result_id, rule_set="side_freestyle_v1", overwrite=True)` 内部解析路径：

```
AnalysisResult.task_id
  → AnalysisTask.session_id
  → TrainingSession
  → SessionVideo (view_type == "side")        # 一个 session 可能多机位，取 side
  → NormalizedAnnotation (该 side video 最新一版)
  → AnnotationMetric (schema_version == "swim-side-metrics.v1")  # 取最新
  → DiagnosticsMetricsAdapter
  → RuleBasedDiagnosticsEngine
  → 写回:
       analysis_results.diagnostics = DiagnosticItem[]
       analysis_results.quality_summary = context.quality_summary
       analysis_results.raw_result["diagnostics_meta"] = {
         rule_set, rule_version, engine_version,
         matched_rule_ids, skipped_rule_ids, generated_at
       }
```

### 7.1 manual_tags 取数来源

桥在构造 adapter 输入时，`manual_tags` 取 `NormalizedAnnotation.manual_tags`（权威来源），仅当其为空才回退 `annotation_metrics.metrics.manual_tags`。见 §2.1。

### 7.2 raw_result 写入安全

写 `raw_result["diagnostics_meta"]` 前，**必须先确保 `raw_result` 是 `{}` 而非 `null`**（已有 `AnalysisResult` 的 `raw_result` 可能为 null）。即：`analysis_result.raw_result = analysis_result.raw_result or {}`，再赋值 `diagnostics_meta`。否则直接写嵌套键会抛 `TypeError`。

### 7.3 错误码（前端与测试据此分支）

| 场景 | HTTP | 含义 |
| --- | --- | --- |
| `analysis_result_id` 不存在 | **404** | 分析结果记录不存在 |
| 记录存在，但解析不到 side `AnnotationMetric` | **422** | 当前分析结果存在，但缺少可用于规则诊断的 side-view metrics |
| 已有 diagnostics 且 `overwrite=false` | **409** | 冲突，需显式 `overwrite=true` 覆盖 |

不静默空跑：上述任一情况都返回明确错误而非空 diagnostics。

## 8. 数据库迁移

**实现修正（已与代码现实对齐）**：`analysis_results.diagnostics` 列**已由迁移 0001
（`create_platform_core_tables`）以 `sa.JSON()` 创建**，本 change 不再重复加列。
因此迁移只新增 `quality_summary`，并补 ORM 模型字段（`app/models/analysis.py`）。

```sql
ALTER TABLE analysis_results
  ADD COLUMN quality_summary JSONB NOT NULL DEFAULT '{}'::jsonb;
```

> 注：表内现有 JSON 列（`detections` / `metrics` / `diagnostics` / `raw_result`）均用
> `sa.JSON()`（PostgreSQL 下映射为 JSONB），故 `quality_summary` 沿用 `sa.JSON()` 保持一致，
> 而非设计原稿写的独立 JSONB 类型。列类型差异不影响诊断逻辑。

`report_builder`（Change #6）已读 `result.diagnostics`（list），新列向后兼容；`raw_result.diagnostics_meta` 供报告首页概览与"为何未判断"解释使用。

## 9. 验收样例（基于 Task #4 实际产物形态）

输入（`annotation_metrics.metrics`）：

```json
{
  "schema_version": "swim-side-metrics.v1",
  "summary": {
    "body_angle_deg_avg": 14.0,
    "hip_depth_cm_avg": 9.0,
    "elbow_angle_deg_avg": 154.0,
    "forearm_drop_angle_deg_avg": 24.0,
    "knee_angle_deg_avg": 114.0,
    "stroke_rate_spm_avg": 82.5,
    "stroke_length_m_avg": 1.06,
    "swolf": { "value": 88.0 }
  },
  "manual_tags": ["front_arm_drop", "low_elbow_catch"]
}
```

adapter 输出 `DiagnosticMetricsContext`：

```json
{
  "body_angle_deg": 14.0,
  "hip_depth_cm": 9.0,
  "elbow_angle_deg": 154.0,
  "forearm_drop_angle_deg": 24.0,
  "knee_angle_deg": 114.0,
  "stroke_rate_spm": 82.5,
  "stroke_length_m": 1.06,
  "swolf_value": 88.0,
  "manual_tags": ["front_arm_drop", "low_elbow_catch"]
}
```

预期命中（active）：R001 / R002 / R004 / R006 / R008 / R009 / R012。其中 **R006 与 R008 同命中，按 §5.1 合并为单个上肢推进主问题**（R008 证据作为 related）。

预期跳过：
- R003 `missing_metric:phase_context`（无 `phase_metrics` / 无 distance_markers，无法分阶段）
- R005 `dormant: requires normalized front reach`
- R007 `missing_metric:catch_area_score`
- R010 `missing_metric:kick_interval_cv`
- R011 `missing_metric:stroke_rate_by_phase,stroke_length_by_phase`

## 10. 目录结构

```
backend/app/services/diagnostics/
  __init__.py
  models.py            # DiagnosticItem / DiagnosticsSummary / DiagnosticsOutput
                       # DiagnosticMetricsContext / RuleEvaluationMeta / SkippedRuleMeta
  adapter.py           # DiagnosticsMetricsAdapter: annotation_metrics → context
  registry.py          # RuleRegistry: 加载/校验 YAML
  evaluator.py         # 仅结构化 all/any 条件评估
  severity.py          # severity + priority_score 解析
  engine.py            # RuleBasedDiagnosticsEngine.run(input) -> DiagnosticsOutput
  recommendation_mapper.py
  bridge.py            # run_diagnostics_for_analysis_result
  rules/
    side_freestyle_v1.yaml
    rule_schema.json
  templates/
    evidence_templates.py
    reason_templates.py
    suggestion_templates.py
```
