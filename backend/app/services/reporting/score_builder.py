from app.services.reporting.section_builder import SEVERITY_RANK


def get_max_severity(findings: list[dict]) -> str | None:
    if not findings:
        return None
    return max(
        (f.get("severity", "low") for f in findings),
        key=lambda s: SEVERITY_RANK.get(s, 0),
    )


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
