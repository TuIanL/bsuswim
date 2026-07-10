from datetime import datetime

from app.models import AnalysisResult, AnalysisTask
from app.services.annotation_quality.models import AnalysisQualitySummary
from app.services.reporting.metric_normalizer import (
    apply_phase_aliases,
    flatten_phase_metrics,
    normalize_report_metrics,
)
from app.services.reporting.recommendation_builder import build_recommendations_section
from app.services.reporting.score_builder import build_diagnostic_load_summary
from app.services.reporting.section_builder import build_sections
from app.services.reporting.summary_builder import build_overview_section, build_summary


def build_report_data(task: AnalysisTask, result: AnalysisResult | None = None) -> dict:
    result = result or task.result
    metrics = result.metrics if result else {}
    diagnostics = result.diagnostics if result else []
    session = task.session
    athlete = session.athlete if session else None
    quality_summary = result.quality_summary if result else {}

    quality_overall = quality_summary.get("decision", {}).get("report_availability", "full") if quality_summary else "full"
    quality_notes: list[str] = []
    if quality_overall == "degraded":
        quality_notes.append("标注或指标质量不足，部分结果仅供参考。")
    elif quality_overall == "blocked":
        quality_notes.append("标注质量不足，无法生成完整报告。")

    return {
        "session": {
            "id": session.id if session else task.session_id,
            "title": session.title if session else "游泳训练分析",
            "session_date": session.session_date.isoformat() if session and session.session_date else None,
            "stroke_type": session.stroke_type.value if session else None,
            "distance_m": session.distance_m if session else None,
            "pool_length_m": float(session.pool_length_m) if session and session.pool_length_m is not None else None,
        },
        "athlete": {
            "id": athlete.id if athlete else None,
            "name": athlete.name if athlete else None,
            "level": athlete.level if athlete else None,
        },
        "summary": {
            "title": session.title if session else "游泳训练分析",
            "stroke_type": session.stroke_type.value if session else "freestyle",
            "overall_score": metrics.get("overall_score", 0),
            "headline": "基于模型服务输出生成的第一版 HTML 报告",
        },
        "metrics": metrics,
        "diagnostics": diagnostics,
        "recommendations": [
            {
                "title": "保持身体中线稳定",
                "target": "降低左右摆动，提高划水效率",
                "linked_issue": diagnostics[0]["title"] if diagnostics else "body_line",
            },
            {
                "title": "分段复盘呼吸节奏",
                "target": "让呼吸动作与划水阶段更稳定同步",
                "linked_issue": "breathing_timing",
            },
        ],
        "charts": {
            "radar": [
                {"name": "身体线", "value": metrics.get("body_line_score", 78)},
                {"name": "节奏", "value": metrics.get("rhythm_score", 82)},
                {"name": "对称性", "value": metrics.get("symmetry_score", 74)},
                {"name": "打腿", "value": metrics.get("kick_score", 76)},
            ]
        },
        "provenance": {
            "task_id": task.id,
            "session_id": task.session_id,
            "source": "model_service",
            "generated_at": datetime.utcnow().isoformat(),
            "schema_version": result.schema_version if result else None,
        },
        "quality_notes": quality_notes,
        "quality_overall": quality_overall,
    }


SWIM_REPORT_FIELDS = {
    "schema_version", "report_mode", "context", "metric_sets",
    "sections", "problem_ranking", "score", "source_trace",
    "quality",
}


def merge_into_existing(existing: dict, swim_report: dict) -> dict:
    merged = dict(existing)

    for key in SWIM_REPORT_FIELDS:
        merged[key] = swim_report[key]

    merged["metrics"] = swim_report["metrics"]
    merged["diagnostics"] = swim_report["diagnostics"]
    merged["charts"] = swim_report.get("charts", {"radar": []})
    merged["recommendations"] = swim_report.get("recommendations", [])
    merged["recommendation_items"] = swim_report.get("recommendation_items", [])
    merged["provenance"] = swim_report["provenance"]

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

    if "quality" in swim_report:
        merged["quality"] = swim_report["quality"]

    return merged


def build_swim_report_data(
    result: AnalysisResult,
    annotation_metric: object,
    diagnostics: list[dict],
    quality_summary: AnalysisQualitySummary | None = None,
) -> dict:
    annotation_metric_id = annotation_metric.id if hasattr(annotation_metric, "id") else None
    raw_metrics = annotation_metric.metrics if hasattr(annotation_metric, "metrics") else {}

    canonical_metrics = normalize_report_metrics(raw_metrics)
    phase_metrics = flatten_phase_metrics(raw_metrics)
    phase_metrics_with_aliases = apply_phase_aliases(phase_metrics)
    merged_metrics = {**canonical_metrics, **phase_metrics_with_aliases}

    sections = build_sections(merged_metrics, diagnostics)
    overview_section = build_overview_section(merged_metrics, diagnostics)
    recs_section = build_recommendations_section(diagnostics)

    # ── inject quality into sections ──
    if quality_summary:
        decision = quality_summary.decision
        module_avail = decision.module_availability
        for section in sections:
            sk = section.get("key")
            if sk and hasattr(module_avail, sk):
                avail = getattr(module_avail, sk)
                section["availability"] = avail
                section["data_confidence"] = "high" if avail == "ready" else ("medium" if avail == "degraded" else "low")
                if avail in ("degraded", "blocked"):
                    section["quality_notes"] = section.get("quality_notes", [])
                    section["quality_notes"].append(f"数据可用性: {avail}")

    all_sections = [overview_section, *sections, recs_section]

    summary = build_summary(merged_metrics, diagnostics, all_sections)
    score = build_diagnostic_load_summary(all_sections)

    task = result.task
    session_id = task.session_id if task else None
    task_id = task.id if task else None

    flat_recs = recs_section.get("_flat_recommendations", [])
    structured_items = recs_section.get("_structured_items", [])

    problem_ranking = [
        {"code": d.get("code"), "title": d["title"], "severity": d.get("severity"), "suggestion": d.get("suggestion")}
        for d in sorted(
            diagnostics,
            key=lambda d: (d.get("priority", 999), {"high": 0, "medium": 1, "low": 2}.get(d.get("severity", "low"), 99)),
        )
    ]

    quality_dict = quality_summary.model_dump(mode="json") if quality_summary else result.quality_summary if hasattr(result, "quality_summary") else {}

    return {
        "schema_version": "swim-report.v1",
        "report_mode": "side_technical",
        "summary": summary,
        "metrics": canonical_metrics,
        "diagnostics": diagnostics,
        "charts": {"radar": []},
        "recommendations": flat_recs,
        "recommendation_items": structured_items,
        "provenance": {
            "source": "annotation_metrics",
            "generated_at": datetime.utcnow().isoformat(),
        },
        "metric_sets": {
            "canonical": canonical_metrics,
            "phase": phase_metrics_with_aliases,
            "raw": raw_metrics,
        },
        "sections": all_sections,
        "problem_ranking": problem_ranking,
        "score": score,
        "context": {
            "analysis_result_id": result.id,
            "annotation_metric_id": annotation_metric_id,
            "session_id": session_id,
            "task_id": task_id,
        },
        "source_trace": {
            "annotation_metric_schema_version": getattr(annotation_metric, "schema_version", None),
            "annotation_metric_id": annotation_metric_id,
            "analysis_result_id": result.id,
        },
        "quality": quality_dict,
    }
