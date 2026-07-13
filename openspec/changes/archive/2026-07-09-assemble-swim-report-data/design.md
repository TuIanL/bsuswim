## Context

当前报告生成 `build_report_data(task, result)` 在 `analysis_service.save_analysis_result()` 内同步执行，直接从 `AnalysisResult.metrics` 读取指标。但过去的 Change #4 和 #5 明确定义了一条独立链路：

```
normalized_annotations → annotation_metrics (Change #4)
annotation_metrics → adapter → diagnostics (Change #5)
```

Change #6 需要把这条链路走通——从 `annotation_metrics` 读取事实指标，从 `analysis_results.diagnostics` 读取诊断，装配为结构化 swim-report.v1。但这不能破坏现有 `save_analysis_result()` 的同步行为，也不能在 T1 强制要求 annotation_metrics（因为 T1 时它未必存在）。

约束总结：

- `save_analysis_result()` 必须保持同步，继续写 legacy report_data
- `annotation_metrics` 和 `diagnostics` 在 T1 时不一定就绪
- 现有 `ReportView.vue` 消费 `report.report.summary.title` / `metrics` / `diagnostics` / `charts.radar`
- 不新增数据库迁移，不新增 ReportMetadata 列
- diagnostics 的 `section_key` 已是报告分节的权威依据

## Goals / Non-Goals

**Goals:**

- 新增 `build_swim_report_data(result, annotation_metric, diagnostics)` 入口，从 `annotation_metrics + diagnostics` 生成 swim-report.v1
- 新增显式 API `POST /api/v1/analysis-results/{id}/build-swim-report` 触发生成
- 输出 swim-report.v1 写入现有 `ReportMetadata.report_data`，与 legacy 字段共存
- metrics 标准化为 canonical unit-aware keys，保留 raw 原始值
- phase_metrics 展平为 `{metric_key}_{phase_key}` 格式
- sections 按 diagnostics 的 `section_key` 分组
- 支持 partial 状态（缺 diagnostics / 部分 section 无数据）；缺 annotation_metrics 应明确报错而非生成空报告
- 前端向后兼容：保留旧 `report.report.metrics` / `diagnostics` / `charts.radar` 结构

**Non-Goals:**

- 不迁移前端到 section-based renderer（Change #7）
- 不做 PDF 导出
- 不做 visual_assets 存储或关键帧截图
- 不做 metric-level evaluation（evaluation 字段允许 null）
- 不做维度评分（score.overall 允许 null）
- 不新增 ReportMetadata 列
- 不修改现有 `save_analysis_result()` 或 legacy `build_report_data()`

## Design

### 1. 数据流总图

```
存储层：
  annotation_metrics.metrics
  analysis_results.diagnostics
  ReportMetadata.report_data

装配层（新增）：
  metric_normalizer.py    ← 读取 raw metrics，输出 canonical + phase + raw
  section_builder.py      ← 读取 diagnostics + metrics，按 section_key 装配 sections
  summary_builder.py      ← 读取 diagnostics，输出 deterministic conclusion
  score_builder.py        ← 读取 sections，输出 diagnostic load summary

API 层（新增）：
  POST /api/v1/analysis-results/{id}/build-swim-report

调用时序：

T1: save_analysis_result()
      → build_report_data(task, result)        ← legacy，不变
      → report_data = {summary, metrics, diagnostics, charts.radar, ...}
      → ReportMetadata.report_data = report_data

T2: calculate_and_persist()
      → write annotation_metrics

T3: run_diagnostics_for_analysis_result()
      → read annotation_metrics
      → write analysis_results.diagnostics

T4: POST /api/v1/analysis-results/{id}/build-swim-report
      → 1. resolve AnnotationMetric (swim-side-metrics.v1)
        2. return 422 如果找不到（metrics 是必要条件）
      → 3. read analysis_result.diagnostics
        3a. diagnostics 为空 → status = partial，不阻塞
      → 4. normalize_report_metrics(raw_metrics)
      → 5. flatten_phase_metrics(raw_metrics)
      → 6. build_sections(metrics, diagnostics)
      → 7. build_summary(diagnostics)
      → 8. build_diagnostic_load_summary(sections)
      → 9. merge into existing ReportMetadata.report_data
      → 10. return {report_id, status: "generated|partial", section_count}
```

### 2. ReportData swim-report.v1 输出结构

```python
{
    "schema_version": "swim-report.v1",
    "report_mode": "side_technical",

    # ── 兼容旧前端字段 ──
    "summary": {
        "title": "游泳专项技术分析报告",
        "overall_score": None,
        "overall_conclusion": "...",
        "top_findings": [],
        "top_recommendations": [],
    },
    "metrics": {  # ← 兼容旧前端，放 canonical flat dict
        "body_angle_deg": 12.4,
        "elbow_angle_deg": 154,
    },
    "diagnostics": [],       # ← 兼容旧前端
    "charts": {"radar": []},       # ← 兼容旧前端，保持空数组
    "recommendations": [],         # ← 兼容旧前端，字符串数组
    "recommendation_items": [],    # ← 新字段，结构化推荐项
    "provenance": {},              # ← 兼容旧前端

    # ── 新字段 ──
    "metric_sets": {
        "canonical": {"body_angle_deg": 12.4, ...},
        "phase": {"body_angle_deg_low_speed": 14, ...},
        "raw": {"body_angle_deg_avg": 12.4, ...},
    },
    "sections": [...],
    "problem_ranking": [...],
    "score": {
        "overall": None,
        "dimensions": [...],
    },
    "context": {
        "analysis_result_id": 123,
        "annotation_metric_id": 901,
        "session_id": 1,
        "task_id": 2,
    },
    "source_trace": {
        "annotation_metric_schema_version": "swim-side-metrics.v1",
        "annotation_metric_id": 901,
        "analysis_result_id": 123,
    },
}
```

`metrics` 顶层兼容旧前端——它直接指向 `metric_sets.canonical` 的引用。`metric_sets` 是新增的完整分层视图。

### 3. Canonical metric 映射

```python
# metric_normalizer.py

METRIC_RENAME = {
    "body_angle_deg_avg": "body_angle_deg",
    "hip_depth_cm_avg": "hip_depth_cm",
    "elbow_angle_deg_avg": "elbow_angle_deg",
    "forearm_drop_angle_deg_avg": "forearm_drop_angle_deg",
    "knee_angle_deg_avg": "knee_angle_deg",
    "hip_angle_deg_avg": "hip_angle_deg",
    "ankle_extension_angle_deg_avg": "ankle_extension_angle_deg",
    "entry_angle_deg_avg": "entry_angle_deg",
    "front_reach_distance_cm_avg": "front_reach_distance_cm",
    "stroke_rate_spm_avg": "stroke_rate_spm",
    "stroke_length_m_avg": "stroke_length_m",
    "average_speed_mps": "speed_mps",
}

# 直接透传（原始键已经是 canonical）
PASS_THROUGH = [
    "streamline_index",
    "technical_stability_score",
    "stroke_count",
    "kick_frequency_hz",
    "swolf_value",
]

def normalize_report_metrics(raw: dict) -> dict:
    """从 annotation_metrics.metrics.summary 标准化为 canonical dict。"""
    summary = raw.get("summary") or raw
    canonical = {}
    for src, dst in METRIC_RENAME.items():
        if src in summary and summary[src] is not None:
            canonical[dst] = summary[src]
    for key in PASS_THROUGH:
        if key in summary and summary[key] is not None:
            canonical[key] = summary[key]
    # swolf 对象展平
    swolf = summary.get("swolf")
    if isinstance(swolf, dict) and "value" in swolf:
        canonical["swolf_value"] = swolf["value"]
    return canonical
```

复用 Change #5 adapter 的映射表（诊断逻辑键 = 报告层 canonical key），保持一致。

### 4. Phase metrics 展平

```python
# metric_normalizer.py

def flatten_phase_metrics(raw: dict) -> dict:
    """
    展平 phase_metrics 嵌套结构。

    输入：
      phase_metrics = [
        {"phase_key": "low_speed", "metrics": {"body_angle_deg": 14}},
        {"phase_key": "middle_speed", "metrics": {"body_angle_deg": 12}},
        {"phase_key": "high_speed", "metrics": {"body_angle_deg": 7}},
      ]

    输出：
      {
        "body_angle_deg_low_speed": 14,
        "body_angle_deg_middle_speed": 12,
        "body_angle_deg_high_speed": 7,
      }
    """
    result = {}
    for phase in raw.get("phase_metrics") or []:
        key = phase.get("phase_key")
        if not key:
            continue
        for m_key, m_val in (phase.get("metrics") or {}).items():
            if m_val is not None:
                result[f"{m_key}_{key}"] = m_val
    return result
```

同时提供 alias 映射用于兼容 Change #5 规则模板中 `{body_angle_low_speed_deg}` 等旧格式。MVP 阶段只 alias body_angle，因为这是目前 rules YAML 中唯一用到的 phase 模板变量。当后续规则引用 `stroke_rate_low_speed_spm` 等新 phase 变量时，再加通用 alias 函数：

```python
# metric_normalizer.py

PHASE_ALIASES = {
    "body_angle_deg_low_speed": "body_angle_low_speed_deg",
    "body_angle_deg_middle_speed": "body_angle_middle_speed_deg",
    "body_angle_deg_high_speed": "body_angle_high_speed_deg",
}

def apply_phase_aliases(flattened: dict) -> dict:
    """追加 phase aliases，不覆盖已有键。"""
    result = dict(flattened)
    for new_key, alias_key in PHASE_ALIASES.items():
        if new_key in flattened and alias_key not in result:
            result[alias_key] = flattened[new_key]
    return result
```

### 5. Section 装配

```python
# section_builder.py

SECTION_CONFIG = {
    "body_position": {
        "title": "身体位置与流线型效率分析",
        "metric_keys": ["body_angle_deg", "hip_depth_cm",
                        "body_angle_deg_low_speed", "body_angle_deg_middle_speed", "body_angle_deg_high_speed"],
    },
    "arm_entry": {
        "title": "上肢入水与前端支撑分析",
        "metric_keys": ["entry_angle_deg", "front_reach_distance_cm", "forearm_drop_angle_deg"],
    },
    "catch_pull": {
        "title": "上肢抱水与推进动作分析",
        "metric_keys": ["elbow_angle_deg", "catch_duration_sec", "pull_duration_sec"],
    },
    "leg_kick": {
        "title": "腿部技术角度分析",
        "metric_keys": ["knee_angle_deg", "hip_angle_deg", "ankle_extension_angle_deg", "kick_frequency_hz"],
    },
    "efficiency": {
        "title": "专项技术效率分析",
        "metric_keys": ["speed_mps", "stroke_rate_spm", "stroke_length_m", "swolf_value"],
    },
}

def build_sections(metrics: dict, diagnostics: list[dict]) -> list[dict]:
    """
    按 diagnostics 的 section_key 分组装配 sections。
    始终输出 SECTION_CONFIG 中定义的 sections，即使无诊断。
    """
    diag_by_section = group_diagnostics_by_section(diagnostics)
    sections = []

    for key, config in SECTION_CONFIG.items():
        diags = diag_by_section.get(key, [])
        section_metrics = [m for m in config["metric_keys"] if m in metrics]

        sections.append({
            "key": key,
            "title": config["title"],
            "status": derive_section_status(diags),
            "metrics": [{"key": k, "value": metrics[k], "evaluation": None} for k in section_metrics],
            "findings": [{"title": d["title"], "severity": d["severity"],
                           "description": d.get("evidence") or d.get("reason", "")}
                         for d in diags],
            "recommendations": [{"title": d["title"], "description": d.get("suggestion", "")}
                                for d in diags if d.get("suggestion")],
            "diagnostic_codes": [d.get("code") for d in diags],
            "assets": [],
        })

    return sections
```

### 6. Overview + Recommendations sections

Fixed sections 追加在 head 和 tail：

```
sections = [
    build_overview_section(metrics, diagnostics, problem_ranking),   # 动态
    ...build_sections(metrics, diagnostics)...,                      # 按 SECTION_CONFIG
    build_recommendations_section(problem_ranking),                  # 动态
]
```

`overview` 不依赖 section_key 分组，直接从顶层 metrics + top diagnostics 构建。

用显式 severity rank 排序，避免字符串字典序错误。

```python
# score_builder.py

SEVERITY_RANK = {
    "high": 3,
    "medium": 2,
    "low": 1,
}

def get_max_severity(findings: list[dict]) -> str | None:
    if not findings:
        return None
    return max(
        (f.get("severity", "low") for f in findings),
        key=lambda s: SEVERITY_RANK.get(s, 0),
    )

def derive_section_status(diagnostics: list[dict]) -> str:
    if not diagnostics:
        return "ok"
    severities = [d.get("severity", "low") for d in diagnostics]
    if "high" in severities:
        return "has_issues"
    if len(diagnostics) >= 3:
        return "has_issues"
    if "medium" in severities:
        return "needs_attention"
    return "minor_issues"

def build_diagnostic_load_summary(sections: list[dict]) -> dict:
    dims = []
    for sec in sections:
        if sec["key"] in ("overview", "recommendations"):
            continue
        dims.append({
            "key": sec["key"],
            "label": sec["title"],
            "issue_count": len(sec["findings"]),
            "max_severity": get_max_severity(sec["findings"]),
            "status": sec["status"],
        })
    return {"overall": None, "dimensions": dims}
```

### 8. Summary template

```python
# summary_builder.py

def build_overall_conclusion(diagnostics: list[dict]) -> str:
    total = len(diagnostics)
    high = sum(1 for d in diagnostics if d.get("severity") == "high")
    medium = sum(1 for d in diagnostics if d.get("severity") == "medium")
    if total == 0:
        return "本次分析未发现明确高优先级技术问题，建议结合教练观察继续复核。"
    if high > 0:
        return f"本次分析发现 {total} 个主要技术问题，其中高严重度问题 {high} 个，建议优先处理。"
    if medium > 0:
        return f"本次分析发现 {total} 个技术问题，主要集中在中等风险项目，建议结合训练周期逐步优化。"
    return f"本次分析发现 {total} 个轻度技术问题，整体表现较稳定，可作为后续复测基线。"

# priority 越小越优先；同 priority 时 high > medium > low
SEVERITY_ORDER = {
    "high": 0,
    "medium": 1,
    "low": 2,
}

def build_top_findings(diagnostics: list[dict], limit: int = 3) -> list[dict]:
    sorted_diags = sorted(diagnostics,
        key=lambda d: (d.get("priority", 999), SEVERITY_ORDER.get(d.get("severity", "low"), 99)))
    return [{"title": d["title"], "severity": d.get("severity")} for d in sorted_diags[:limit]]

def build_top_recommendations(diagnostics: list[dict], limit: int = 3) -> list[str]:
    sorted_diags = sorted(diagnostics,
        key=lambda d: (d.get("priority", 999), SEVERITY_ORDER.get(d.get("severity", "low"), 99)))
    return [d.get("suggestion", "") for d in sorted_diags[:limit] if d.get("suggestion")]
```

### 9. Resolver：定位 AnnotationMetric

```python
# reporting/resolver.py

def resolve_annotation_metric_for_result(
    db: Session,
    analysis_result: AnalysisResult,
    *,
    schema_version: str = "swim-side-metrics.v1",
    camera_view: str = "side",
) -> AnnotationMetric | None:
    """
    查找与 analysis_result 关联的 side-view AnnotationMetric。

    优先路径：
      1. diagnostics_meta / raw_result 里有直接 annotation_metric_id
      2. 回退：result → task → session → side_video → NormalizedAnnotation → AnnotationMetric
    """
    # path 1: 检查 raw_result 中的直接引用
    meta = (analysis_result.raw_result or {}).get("diagnostics_meta") or {}
    if meta.get("annotation_metric_id"):
        metric = db.get(AnnotationMetric, meta["annotation_metric_id"])
        if metric and metric.schema_version == schema_version:
            return metric

    # path 2: 遍历 task → session → video → norm → metric
    task = analysis_result.task
    if not task or not task.session:
        return None
    side_video = next((v for v in task.session.videos if v.view_type == ViewType.SIDE), None)
    if not side_video:
        return None
    norm = db.scalars(
        select(NormalizedAnnotation)
        .where(NormalizedAnnotation.session_video_id == side_video.id)
        .order_by(NormalizedAnnotation.id.desc())
    ).first()
    if not norm:
        return None
    return db.scalars(
        select(AnnotationMetric)
        .where(
            AnnotationMetric.normalized_annotation_id == norm.id,
            AnnotationMetric.schema_version == schema_version,
        )
        .order_by(AnnotationMetric.id.desc())
    ).first()
```

### 9a. API

```python
# routes/reports.py 新增

@router.post("/reports/from-analysis-results/{analysis_result_id}/swim")
def build_swim_report(analysis_result_id: int, db: Session, ...):
    result = db.get(AnalysisResult, analysis_result_id)
    if not result:
        raise HTTPException(404)

    annotation_metric = resolve_annotation_metric_for_result(db, result)
    if not annotation_metric:
        raise HTTPException(422, detail="annotation_metrics 未就绪，请先完成指标计算")

    # diagnostics 为空时不阻塞，但标记 partial
    diagnostics = result.diagnostics or []
    is_partial = len(diagnostics) == 0

    report_data = build_swim_report_data(result, annotation_metric, diagnostics)
    if is_partial:
        report_data["status"] = "partial"
        report_data.setdefault("warnings", []).append("diagnostics_empty")

    task = result.task
    report = db.scalar(select(ReportMetadata).where(ReportMetadata.session_id == task.session_id))
    if report:
        report.report_data = merge_into_existing(report.report_data or {}, report_data)
        report.source = "kinovea_assisted"
    else:
        report = ReportMetadata(session_id=task.session_id, task_id=task.id,
                                source="kinovea_assisted", report_data=report_data)
    db.add(report)
    db.commit()

    return {
        "report_id": report.id,
        "status": "partial" if is_partial else "generated",
        "section_count": len(report_data.get("sections", [])),
        "warnings": report_data.get("warnings", []),
    }
```

### 10. merge 策略

`build_swim_report_data` 输出 swim-report.v1 字段，与 ReportMetadata 中已有的 legacy 字段合并。兼容字段（`metrics` / `diagnostics` / `charts` / `recommendations`）用 swim 版本更新，`summary.title` 保留 legacy 值（等前端迁移后再移除）：

```python
SWIM_REPORT_FIELDS = {"schema_version", "report_mode", "context", "metric_sets",
                       "sections", "problem_ranking", "score", "source_trace"}

def merge_into_existing(existing: dict, swim_report: dict) -> dict:
    merged = dict(existing)

    # 新增 swim-report.v1 专属字段
    for key in SWIM_REPORT_FIELDS:
        merged[key] = swim_report[key]

    # 更新兼容字段为 swim 版本（使旧前端能看到最新指标）
    merged["metrics"] = swim_report["metrics"]
    merged["diagnostics"] = swim_report["diagnostics"]
    merged["charts"] = swim_report.get("charts", {"radar": []})
    merged["recommendations"] = swim_report.get("recommendations", [])
    merged["recommendation_items"] = swim_report.get("recommendation_items", [])
    merged["provenance"] = swim_report["provenance"]

    # summary：保留 legacy title/overall_score，追加 swim 新字段
    legacy_summary = merged.get("summary") or {}
    swim_summary = swim_report["summary"]
    merged["summary"] = {
        **legacy_summary,
        "title": legacy_summary.get("title") or swim_summary.get("title"),
        "overall_score": legacy_summary.get("overall_score"),
        "overall_conclusion": swim_summary.get("overall_conclusion"),
        "top_findings": swim_summary.get("top_findings", []),
        "top_recommendations": swim_summary.get("top_recommendations", []),
    }

    return merged
```

## Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | 拆双轨，不替换现有 `build_report_data` | T1 时 annotation_metrics 可能不存在，不能阻塞 save_analysis_result |
| D2 | 显式 API 触发 swim-report.v1 生成 | 让调用方明确知道什么时候输入完备，避免隐式 partial 报告 |
| D3 | ReportData 存回同一 `ReportMetadata.report_data` | 不新增表、不迁移，前端 URL 不变，`GET /reports/{session_id}` 仍有效 |
| D4 | `metrics` 顶层放 canonical flat dict 兼容旧前端 | 避免炸前端，`ReportView.vue` 的 `report.report.metrics` 继续有效 |
| D5 | section key 直接等于 rules YAML 的 `section_key` | 避免第二套命名，与 Change #5 保持一致 |
| D6 | Phase 展平用 `{metric_key}_{phase_key}` | 按指标聚合便于 section 内查找，规则模板 alias 短期兼容 |
| D7 | Evaluation 允许 null | 不在 Change #6 造 mini rule engine，metric-level 评价延后 |
| D8 | 不新增 ReportMetadata 列 | schema_version/report_mode 写入 JSON，等需要索引时再加 |
| D9 | Summary 用统计模板不做 NLG | 简单可靠，5 个模板分支覆盖所有情况 |

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| 调用方未知 swim-report 生成 API 的存在 | 前端先不主动调用，等 Change #7 前端 section renderer 接入时再暴露入口 |
| `ReportMetadata.report_data` 膨胀 | 目标结构可控（~50-100 行 JSON），远未达到 JSONB 性能瓶颈 |
| Legacy 字段和 swim-report 字段重叠（如 `summary`） | 采用 merge 策略，新字段追加，旧字段不删 |
| 旧 `ReportView.vue` 读不到 swim-report 的 sections | sections 是新增字段，不影响旧 Consumer 读取现有字段 |
| annotation_metrics 查询链路长（result → task → session → video → norm → metric） | 可复用 Change #5 bridge 的 `resolve_annotation_metric_for_result` 逻辑，或增加轻量 direct FK |
