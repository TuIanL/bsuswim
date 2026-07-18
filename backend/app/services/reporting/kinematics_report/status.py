"""Section and report assembly status derivation."""

from app.schemas.kinematics_report import (
    AssemblyStatus,
    FivePageReportSection,
    ReportMetric,
    SectionStatus,
)
from .constants import PAGE_READINESS_POLICY


def _group_available(keys: list[str], metrics: list[ReportMetric]) -> bool:
    """Check if any metric in the group is available or low_confidence."""
    metric_keys = {m.key for m in metrics}
    return any(k in metric_keys for k in keys)


def _group_all_ready(keys: list[str], metrics: list[ReportMetric]) -> bool:
    """Check if all metrics in the group are available (not low_confidence or unavailable)."""
    by_key = {m.key: m for m in metrics}
    for k in keys:
        m = by_key.get(k)
        if m is None or m.availability != "available":
            return False
    return True


def _any_low_confidence(metrics: list[ReportMetric]) -> bool:
    return any(m.availability == "low_confidence" for m in metrics)


def _preferred_assets_available(
    asset_keys: list[str], asset_keys_present: set[str]
) -> bool:
    for group in asset_keys:
        if any(ak in asset_keys_present for ak in group):
            return True
    return False


def derive_section_status(
    page_type: str,
    metrics: list[ReportMetric],
    asset_keys_present: set[str],
    upstream_status: str | None,
) -> SectionStatus:
    """Derive section.status from policy."""
    policy = PAGE_READINESS_POLICY.get(page_type)
    if policy is None:
        if not metrics and not asset_keys_present:
            return "unavailable"
        return "ready"

    required_groups = policy.get("required_metric_groups", [])
    preferred_groups = policy.get("preferred_asset_groups", [])

    if required_groups:
        any_available = any(
            _group_available(group, metrics) for group in required_groups
        )
        if not any_available:
            return "unavailable"

    all_ready = all(
        _group_all_ready(group, metrics) for group in required_groups
    ) if required_groups else True

    has_low_conf = _any_low_confidence(metrics)
    assets_ok = _preferred_assets_available(preferred_groups, asset_keys_present)
    upstream_ok = upstream_status in (None, "ready")

    if all_ready and assets_ok and not has_low_conf and upstream_ok:
        return "ready"
    return "partial"


def derive_assembly_status(
    sections: list[FivePageReportSection],
    artifact_resolution: str | None,
    finding_available: bool,
) -> AssemblyStatus:
    """Derive top-level assembly_status."""
    tech_pages = [s for s in sections if s.page_type not in ("analysis_overview", "review_and_retest")]
    if any(s.status == "unavailable" for s in tech_pages):
        return "partial"
    if artifact_resolution and artifact_resolution not in ("current_ready", "current_partial"):
        return "partial"
    if not finding_available:
        return "partial"

    has_partial = any(s.status == "partial" for s in sections)
    if has_partial:
        return "partial"
    return "ready"
