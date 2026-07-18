"""Report generation signature."""

import hashlib
import json

from app.models.kinematic_artifact import KinematicArtifactSet
from app.models.kinematic_review_finding import KinematicReviewFindingSet


def _stable_hash(obj) -> str:
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compute_report_signature(
    *,
    annotation_metric_id: int,
    source_revision: int | None,
    metric_payload_hash: str,
    artifact_signature: str | None,
    artifact_manifest_sha256: str | None,
    finding_signature: str | None,
    finding_payload_hash: str | None,
    report_config_hash: str,
) -> str:
    """Compute deterministic report generation signature."""
    payload = {
        "annotation_metric_id": annotation_metric_id,
        "source_revision": source_revision,
        "metric_payload_hash": metric_payload_hash,
        "artifact_set_signature": artifact_signature or "missing",
        "artifact_manifest_sha256": artifact_manifest_sha256 or "missing",
        "finding_set_signature": finding_signature or "missing",
        "finding_payload_hash": finding_payload_hash or "missing",
        "report_config_hash": report_config_hash,
    }
    return _stable_hash(payload)


def compute_report_config_hash(
    kin_report_metrics: dict,
    page_metric_keys: dict,
    page_plan: dict,
    page_readiness_policy: dict,
    retest_core_keys: list,
    asset_order: dict,
    finding_limits: dict,
) -> str:
    return _stable_hash({
        "kin_report_metrics": kin_report_metrics,
        "page_metric_keys": page_metric_keys,
        "page_plan": page_plan,
        "page_readiness_policy": page_readiness_policy,
        "retest_core_keys": retest_core_keys,
        "asset_order": asset_order,
        "finding_limits": finding_limits,
    })


def compute_finding_payload_hash(finding_set: KinematicReviewFindingSet | None) -> str:
    if finding_set is None:
        return "missing"
    findings_raw = getattr(finding_set, "findings", [])
    summary = getattr(finding_set, "summary", {})
    warnings = getattr(finding_set, "warnings", [])
    skipped = getattr(finding_set, "skipped_rules", [])
    return _stable_hash({
        "findings": findings_raw,
        "summary": summary,
        "warnings": warnings,
        "skipped_rules": skipped,
    })
