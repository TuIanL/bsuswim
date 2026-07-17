from app.schemas.normalized_annotation import AnalysisReadiness
from app.services.annotation_quality.legacy import normalize_quality_payload


def derive_analysis_readiness(quality: dict) -> AnalysisReadiness | None:
    if not quality:
        return None
    report = normalize_quality_payload(quality)
    status = report.status
    blocking_count = report.summary.blocking_count
    affected = [
        mk for mk, mr in report.module_readiness.items()
        if mr.status in ("degraded", "blocked")
    ]
    if status == "valid":
        return AnalysisReadiness(
            can_submit=True, requires_acknowledgement=False,
            blocking_issue_count=0, affected_modules=[],
        )
    if status == "warning":
        return AnalysisReadiness(
            can_submit=True, requires_acknowledgement=True,
            blocking_issue_count=0, affected_modules=affected,
        )
    return AnalysisReadiness(
        can_submit=False, requires_acknowledgement=False,
        blocking_issue_count=blocking_count, affected_modules=affected,
    )
