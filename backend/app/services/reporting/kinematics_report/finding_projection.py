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


def _project_evidence_metric(em: FindingEvidenceMetric) -> ReportFindingEvidenceMetric:
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


def _project_evidence_frame(ef: FindingEvidenceFrame) -> ReportFindingEvidenceFrame:
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


def project_finding(f: KinematicReviewFinding) -> ReportFinding:
    return ReportFinding(
        code=f.code,
        rule_id=f.rule_id,
        title=f.title,
        category=f.category,  # type: ignore[arg-type]
        status=f.status,
        attention_level=f.attention_level,
        priority=f.priority,
        priority_score=f.priority_score,
        evidence_metrics=[_project_evidence_metric(em) for em in f.evidence_metrics],
        evidence_frames=[_project_evidence_frame(ef) for ef in f.evidence_frames],
        confidence=f.confidence,
        confidence_level=f.confidence_level,
        limitations=list(f.limitations),
        review_question=f.review_question,
        threshold_basis=f.threshold_basis,
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
