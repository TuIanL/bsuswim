SEVERITY_ORDER = {
    "high": 0,
    "medium": 1,
    "low": 2,
}


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


def build_top_findings(diagnostics: list[dict], limit: int = 3) -> list[dict]:
    sorted_diags = sorted(
        diagnostics,
        key=lambda d: (d.get("priority", 999), SEVERITY_ORDER.get(d.get("severity", "low"), 99)),
    )
    return [{"title": d["title"], "severity": d.get("severity")} for d in sorted_diags[:limit]]


def build_top_recommendations(diagnostics: list[dict], limit: int = 3) -> list[str]:
    sorted_diags = sorted(
        diagnostics,
        key=lambda d: (d.get("priority", 999), SEVERITY_ORDER.get(d.get("severity", "low"), 99)),
    )
    return [d.get("suggestion", "") for d in sorted_diags[:limit] if d.get("suggestion")]


def build_overview_section(metrics: dict, diagnostics: list[dict]) -> dict:
    top_findings = build_top_findings(diagnostics, limit=5)
    top_recs = build_top_recommendations(diagnostics, limit=3)

    return {
        "key": "overview",
        "type": "overview",
        "title": "测试概况与核心结果总览",
        "status": "complete",
        "summary": build_overall_conclusion(diagnostics),
        "metrics": [{"key": k, "value": v, "evaluation": None} for k, v in metrics.items()],
        "findings": top_findings,
        "recommendations": [{"title": r} for r in top_recs],
        "diagnostic_codes": [],
        "assets": [],
    }


def build_summary(metrics: dict, diagnostics: list[dict], sections: list[dict]) -> dict:
    return {
        "title": "游泳专项技术分析报告",
        "overall_score": None,
        "overall_conclusion": build_overall_conclusion(diagnostics),
        "top_findings": build_top_findings(diagnostics),
        "top_recommendations": build_top_recommendations(diagnostics),
    }
