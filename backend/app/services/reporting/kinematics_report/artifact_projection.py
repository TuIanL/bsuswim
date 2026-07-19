"""Report asset projection and cross-side keyframe selection."""

import os
from typing import Optional

from app.schemas.kinematic_artifact import KinematicArtifactRead, KinematicArtifactSetRead
from app.schemas.kinematics_report import ReportAsset


def project_to_report_assets_extended(artifact_set) -> list[ReportAsset]:
    """Project ready artifacts into ReportAsset list with full trace fields.

    Accepts either a KinematicArtifactSet ORM object or a KinematicArtifactSetRead.
    Skipped/failed artifacts are excluded (caller should convert them to quality_notes).
    """
    results: list[ReportAsset] = []
    artifacts = getattr(artifact_set, "artifacts", [])
    for art in artifacts:
        if getattr(art, "status", None) != "ready":
            continue
        storage_path = getattr(art, "storage_path", None)
        if not storage_path:
            continue

        from app.services.storage import public_asset_url
        url = public_asset_url(storage_path)

        artifact_type = getattr(art, "artifact_type", "")
        report_type = "annotated_frame" if artifact_type == "annotated_keyframe" else "image"

        meta = getattr(art, "artifact_metadata", None)
        if meta is None:
            meta = getattr(art, "metadata", None)
        if meta is None:
            meta = {}
        if hasattr(meta, "model_dump"):
            meta = meta.model_dump(mode="json")

        pres = getattr(art, "presentation", None)

        results.append(ReportAsset(
            key=getattr(art, "artifact_key", ""),
            type=report_type,
            title=pres.title if pres and pres.title else getattr(art, "artifact_key", ""),
            url=url,
            artifact_type=artifact_type,
            module_key=getattr(art, "module_key", ""),
            metric_keys=list(getattr(art, "metric_keys", [])),
            annotation_frame=getattr(art, "annotation_frame", None),
            source_video_frame=getattr(art, "source_video_frame", None),
            width=getattr(art, "width", None),
            height=getattr(art, "height", None),
            mime_type=getattr(art, "mime_type", None),
            checksum_sha256=getattr(art, "checksum_sha256", None),
            label=pres.label if pres else getattr(art, "artifact_key", ""),
            value=pres.value if pres else None,
            caption=pres.caption if pres else None,
            source_annotation_revision=getattr(art, "source_annotation_revision", None),
            generator_version=getattr(art, "generator_version", None),
            metadata=meta,
        ))
    return results


def collect_skipped_artifact_quality_notes(artifact_set) -> list[dict]:
    """Convert skipped/failed artifacts into quality notes."""
    notes = []
    artifacts = getattr(artifact_set, "artifacts", [])
    for art in artifacts:
        status = getattr(art, "status", None)
        skip_reason = getattr(art, "skip_reason", None)
        status_detail = getattr(art, "status_detail", None)
        if status in ("skipped", "failed"):
            msg = f"资产 {getattr(art, 'artifact_key', 'unknown')}"
            if skip_reason:
                msg += f": {skip_reason}"
            if status_detail:
                msg += f" ({status_detail})"
            notes.append({
                "code": skip_reason or f"artifact_{status}",
                "level": "warning",
                "message": msg,
            })
    return notes


def _select_best_keyframe(
    artifacts_by_key: dict[str, ReportAsset],
    left_key: str,
    right_key: str,
    pick_min: bool,
) -> Optional[ReportAsset]:
    """Select the best keyframe across left/right sides."""
    left = artifacts_by_key.get(left_key)
    right = artifacts_by_key.get(right_key)
    candidates = []
    if left is not None:
        candidates.append((left.value, left))
    if right is not None:
        candidates.append((right.value, right))
    if not candidates:
        return None
    candidates.sort(key=lambda x: float(x[0] or 0), reverse=not pick_min)
    return candidates[0][1]


def select_cross_side_keyframes(
    assets: list[ReportAsset],
) -> tuple[Optional[ReportAsset], Optional[ReportAsset], Optional[ReportAsset], Optional[ReportAsset]]:
    """Select cross-side keyframes for upper and lower limbs.

    Returns:
        (elbow_flexion, elbow_extension, knee_flexion, knee_extension)
    """
    by_key = {a.key: a for a in assets}

    elbow_flexion = _select_best_keyframe(
        by_key,
        "upper_limb.keyframe.left_elbow_min",
        "upper_limb.keyframe.right_elbow_min",
        pick_min=True,
    )
    elbow_extension = _select_best_keyframe(
        by_key,
        "upper_limb.keyframe.left_elbow_max",
        "upper_limb.keyframe.right_elbow_max",
        pick_min=False,
    )
    knee_flexion = _select_best_keyframe(
        by_key,
        "lower_limb.keyframe.left_knee_min",
        "lower_limb.keyframe.right_knee_min",
        pick_min=True,
    )
    knee_extension = _select_best_keyframe(
        by_key,
        "lower_limb.keyframe.left_knee_max",
        "lower_limb.keyframe.right_knee_max",
        pick_min=False,
    )
    return elbow_flexion, elbow_extension, knee_flexion, knee_extension
