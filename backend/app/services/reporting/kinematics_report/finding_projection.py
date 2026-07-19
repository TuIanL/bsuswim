"""Review finding projection and ordering."""

from app.schemas.kinematic_review_finding import (
    FindingEvidenceFrame,
    FindingEvidenceMetric,
    KinematicReviewFinding,
    ReviewFindingsSummary,
)
from app.schemas.kinematics_report import (
    ReportFinding,
    ReportFindingEvidenceFrame,
    ReportFindingEvidenceMetric,
)
from .constants import ATTENTION_RANK


def _project_evidence_metric(em: FindingEvidenceMetric | dict) -> ReportFindingEvidenceMetric:
    if isinstance(em, dict):
        return ReportFindingEvidenceMetric(
            key=em.get("key"),
            source_metric_keys=list(em.get("source_metric_keys") or []),
            derivation=em.get("derivation"),
            label=em.get("label"),
            value=em.get("value"),
            unit=em.get("unit"),
            availability=em.get("availability"),
            confidence=em.get("confidence"),
            comparison=em.get("comparison"),
            threshold=em.get("threshold"),
            reference_basis=em.get("reference_basis"),
        )
    return ReportFindingEvidenceMetric(
        key=em.key,
        source_metric_keys=list(em.source_metric_keys),
        derivation=em.derivation,
        label=em.label,
        value=em.value,
        unit=em.unit,
        availability=em.availability,
        confidence=em.confidence,
        comparison=em.comparison,
        threshold=em.threshold,
        reference_basis=em.reference_basis,
    )


def _project_evidence_frame(ef: FindingEvidenceFrame | dict) -> ReportFindingEvidenceFrame:
    if isinstance(ef, dict):
        return ReportFindingEvidenceFrame(
            metric_key=ef.get("metric_key"),
            annotation_frame=ef.get("annotation_frame"),
            source_video_frame=ef.get("source_video_frame"),
            time_sec=ef.get("time_sec"),
            role=ef.get("role"),
            value=ef.get("value"),
            extractable=ef.get("extractable"),
            mapping_status=ef.get("mapping_status"),
        )
    return ReportFindingEvidenceFrame(
        metric_key=ef.metric_key,
        annotation_frame=ef.annotation_frame,
        source_video_frame=ef.source_video_frame,
        time_sec=ef.time_sec,
        role=ef.role,
        value=ef.value,
        extractable=ef.extractable,
        mapping_status=ef.mapping_status,
    )


def project_finding(f: KinematicReviewFinding | dict) -> ReportFinding:
    if isinstance(f, dict):
        def _get(attr):
            return f.get(attr)
        evidence_metrics_raw = f.get("evidence_metrics") or []
        evidence_frames_raw = f.get("evidence_frames") or []
    else:
        def _get(attr):
            return getattr(f, attr, None)
        evidence_metrics_raw = f.evidence_metrics
        evidence_frames_raw = f.evidence_frames

    return ReportFinding(
        code=_get("code"),
        rule_id=_get("rule_id"),
        title=_get("title"),
        category=_get("category"),  # type: ignore[arg-type]
        status=_get("status"),
        attention_level=_get("attention_level"),
        priority=_get("priority"),
        priority_score=_get("priority_score"),
        evidence_metrics=[_project_evidence_metric(em) for em in evidence_metrics_raw],
        evidence_frames=[_project_evidence_frame(ef) for ef in evidence_frames_raw],
        confidence=_get("confidence"),
        confidence_level=_get("confidence_level"),
        limitations=list(_get("limitations") or []),
        review_question=_get("review_question"),
        threshold_basis=_get("threshold_basis"),
    )


def sort_findings(findings: list[ReportFinding]) -> list[ReportFinding]:
    """Deterministic sort: priority ASC, priority_score DESC, attention_rank ASC, confidence ASC, code ASC."""
    return sorted(
        findings,
        key=lambda f: (
            f.priority,
            -f.priority_score,
            ATTENTION_RANK.get(f.attention_level, 99),
            -f.confidence,
            f.code,
        ),
    )


def group_findings_by_category(
    findings: list[ReportFinding],
) -> dict[str, list[ReportFinding]]:
    """Group sorted findings by category."""
    grouped: dict[str, list[ReportFinding]] = {}
    for f in sort_findings(findings):
        grouped.setdefault(f.category, []).append(f)
    return grouped


def project_and_sort_findings(
    findings: list[KinematicReviewFinding],
) -> list[ReportFinding]:
    """Project and sort findings in one call."""
    return sort_findings([project_finding(f) for f in findings])
