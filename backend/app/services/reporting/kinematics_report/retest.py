"""Retest metric resolution: maps finding evidence to canonical metric keys."""

from typing import Optional

from app.schemas.kinematic_review_finding import FindingEvidenceMetric
from app.schemas.kinematics_report import (
    ReportFinding,
    ReportMetric,
    RetestMetric,
    StatType,
)


def _resolve_source_metric_keys(
    evidence: FindingEvidenceMetric,
) -> list[tuple[str, Optional[StatType]]]:
    """Resolve finding evidence metric to canonical metric keys.

    Parses source_metric_keys (e.g. "ranges.left_knee_angle_deg.p05")
    into (canonical_key, statistic) pairs.
    Handles reference_body_length.* as non-canonical (skipped).
    """
    results: list[tuple[str, Optional[StatType]]] = []
    for raw in evidence.source_metric_keys:
        if raw.startswith("reference_body_length."):
            continue
        if "." not in raw:
            results.append((raw, None))
            continue

        parts = raw.split(".")
        if parts[0] == "summary":
            results.append((parts[1], None))
        elif parts[0] == "ranges":
            metric_key = parts[1]
            stat_raw = parts[2] if len(parts) > 2 else None
            stat: Optional[StatType] = None
            if stat_raw in ("min", "max", "p05", "p50", "p95", "mean", "std"):
                stat = stat_raw  # type: ignore[assignment]
            results.append((metric_key, stat))
            # type: ignore[generalTypeIssue]
        else:
            results.append((raw, None))
    return results


def resolve_retest_source_metric_keys(
    evidence: FindingEvidenceMetric,
) -> list[str]:
    """Public API: resolve to canonical metric key strings only."""
    return [k for k, _ in _resolve_source_metric_keys(evidence)]


def build_retest_metrics(
    all_report_metrics: dict[str, ReportMetric],
    findings: list[ReportFinding],
    displayed_metric_keys: set[str],
    retest_core_keys: list[str],
) -> list[RetestMetric]:
    """Build retest metric list from the shared index.

    Three-tier priority:
    1. Finding evidence metrics resolved to canonical keys
    2. low_confidence page core metrics
    3. displayed RETEST_CORE_KEYS
    """
    seen: set[str] = set()
    retest: list[RetestMetric] = []

    # Tier 1: from findings
    for f in findings:
        for em in f.evidence_metrics:
            canonical_keys = resolve_retest_source_metric_keys(em)
            for ck in canonical_keys:
                if ck in seen or ck not in all_report_metrics:
                    continue
                m = all_report_metrics[ck]
                seen.add(ck)
                retest.append(RetestMetric(
                    metric_key=ck,
                    label=m.label,
                    current_value=m.value,
                    display_value=m.display_value,
                    unit=m.unit,
                    reference_basis=m.reference_basis,
                    trigger_metric_key=em.key,
                    derivation=em.derivation,
                    reason=f"来自复核发现「{f.title}」的证据指标",
                ))

    # Tier 2: low_confidence
    for key in displayed_metric_keys:
        if key in seen:
            continue
        m = all_report_metrics.get(key)
        if m is None or m.availability != "low_confidence":
            continue
        seen.add(key)
        retest.append(RetestMetric(
            metric_key=key,
            label=m.label,
            current_value=m.value,
            display_value=m.display_value,
            unit=m.unit,
            reference_basis=m.reference_basis,
            reason="低置信度指标，建议复测确认",
        ))

    # Tier 3: RETEST_CORE_KEYS
    for key in retest_core_keys:
        if key in seen:
            continue
        if key not in displayed_metric_keys:
            continue
        m = all_report_metrics.get(key)
        if m is None:
            continue
        seen.add(key)
        retest.append(RetestMetric(
            metric_key=key,
            label=m.label,
            current_value=m.value,
            display_value=m.display_value,
            unit=m.unit,
            reference_basis=m.reference_basis,
            reason="核心复测指标",
        ))

    return retest
