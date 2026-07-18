"""Current artifact-set resolver — resolves a KinematicArtifactSet by expected signature.

This resolver is independent from the review-finding resolver. Each product type
has its own signature formula (artifacts include video checksum, style hash, etc.).
They only share low-level hashing utilities (canonical_json, metric_hash).
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AnnotationMetric, KinematicArtifactSet, NormalizedAnnotation, VideoFile
from app.schemas.kinematics_report import ArtifactResolutionResult, ResolutionStatus
from app.services.kinematic_artifacts.constants import (
    ARTIFACT_PLAN_VERSION,
    GENERATOR_VERSION,
    STYLE_PROFILE,
    ArtifactSetStatus,
)
from app.services.kinematic_artifacts.signature import generation_signature, metric_hash
from app.services.kinematic_artifacts.stability_index import config_hash as stability_config_hash


def _style_profile_hash() -> str:
    import hashlib
    import json

    from app.services.kinematic_artifacts.constants import KEYFRAME_HEIGHT, KEYFRAME_WIDTH

    payload = {
        "style_profile": STYLE_PROFILE,
        "keyframe_w": KEYFRAME_WIDTH,
        "keyframe_h": KEYFRAME_HEIGHT,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def compute_expected_artifact_signature(
    metric: AnnotationMetric,
    annotation: NormalizedAnnotation,
    video_file: Optional[VideoFile],
) -> str:
    """Compute the expected artifact generation signature without side effects."""
    mhash = metric_hash(metric.metrics if isinstance(metric.metrics, dict) else {})
    video_checksum = video_file.checksum_sha256 if video_file else None
    return generation_signature(
        annotation_metric_id=metric.id,
        source_annotation_revision=metric.source_revision,
        source_metric_hash=mhash,
        source_video_checksum=video_checksum,
        generator_version=GENERATOR_VERSION,
        artifact_plan_version=ARTIFACT_PLAN_VERSION,
        style_profile=STYLE_PROFILE,
        style_profile_hash=_style_profile_hash(),
        stability_index_config_hash=stability_config_hash(),
    )


def resolve_current_artifact_set(
    db: Session,
    metric: AnnotationMetric,
    annotation: NormalizedAnnotation,
    video_file: Optional[VideoFile],
) -> ArtifactResolutionResult:
    """Resolve the current artifact set by expected artifact signature.

    This is an internal resolver — it does NOT check ownership.
    Ownership validation should be done once in the assembly service
    before calling this function.
    """
    sig = compute_expected_artifact_signature(metric, annotation, video_file)

    artifact_set: Optional[KinematicArtifactSet] = db.scalar(
        select(KinematicArtifactSet).filter_by(
            annotation_metric_id=metric.id,
            generation_signature=sig,
        )
    )

    if artifact_set is None:
        return ArtifactResolutionResult(
            artifact_set=None,
            resolution_status="not_generated",
            warning_code="artifacts_not_generated",
        )

    status: str = artifact_set.status
    status_map: dict[str, tuple[ResolutionStatus, str | None]] = {
        ArtifactSetStatus.READY: ("current_ready", None),
        ArtifactSetStatus.PARTIAL: ("current_partial", None),
        ArtifactSetStatus.GENERATING: ("current_generating", "artifacts_generating"),
        ArtifactSetStatus.FAILED: ("current_failed", "artifacts_generation_failed"),
    }
    resolution_status, warning_code = status_map.get(
        status, ("not_generated", "artifacts_unknown_status")
    )
    return ArtifactResolutionResult(
        artifact_set=artifact_set,
        resolution_status=resolution_status,
        warning_code=warning_code,
    )
