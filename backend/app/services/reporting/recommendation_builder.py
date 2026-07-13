def build_recommendations_section(diagnostics: list[dict]) -> dict:
    sorted_diags = sorted(
        diagnostics,
        key=lambda d: (
            d.get("priority", 999),
            {"high": 0, "medium": 1, "low": 2}.get(d.get("severity", "low"), 99),
        ),
    )

    items = []
    flat_recs: list[str] = []
    for d in sorted_diags:
        suggestion = d.get("suggestion", "")
        if suggestion:
            flat_recs.append(suggestion)
            items.append({
                "diagnostic_code": d.get("code"),
                "title": d["title"],
                "description": suggestion,
                "severity": d.get("severity"),
            })

    return {
        "key": "recommendations",
        "type": "recommendation_plan",
        "title": "关键问题排序与训练建议",
        "status": "complete",
        "summary": "建议优先处理高严重度问题，并设置可复测的技术目标。",
        "metrics": [],
        "findings": [
            {
                "title": d["title"],
                "severity": d["severity"],
                "description": d.get("evidence") or d.get("reason", ""),
            }
            for d in sorted_diags
        ],
        "recommendations": items,
        "diagnostic_codes": [d.get("code") for d in sorted_diags if d.get("code")],
        "assets": [],
        "_flat_recommendations": flat_recs,
        "_structured_items": items,
    }
