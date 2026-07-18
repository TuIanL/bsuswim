"""Manifest payload builder and report-asset projection."""

import hashlib
import json

from app.models.annotation_metric import AnnotationMetric
from app.models.kinematic_artifact import KinematicArtifact, KinematicArtifactSet
from app.services.kinematic_artifacts.constants import GENERATOR_NAME, GENERATOR_VERSION, STYLE_PROFILE
from app.services.kinematic_artifacts.stability_index import config_hash
from app.services.storage import public_asset_url


def _presentation(art: KinematicArtifact) -> dict | None:
    if art.artifact_type == "annotated_keyframe":
        return {
            "title": art.artifact_key.split(".")[-1],
            "label": art.artifact_key,
            "value": (art.artifact_metadata or {}).get("value"),
            "caption": "基于二维骨架几何的客观指标。",
            "report_asset_type": "annotated_frame",
        }
    return {
        "title": art.artifact_key.split(".")[-1],
        "label": art.artifact_key,
        "report_asset_type": "image",
    }


def build_manifest_payload(
    artifact_set: KinematicArtifactSet,
    artifacts: list[KinematicArtifact],
    metric: AnnotationMetric,
    video_checksum: str | None,
) -> dict:
    out_artifacts = []
    for art in sorted(artifacts, key=lambda a: a.artifact_key):
        out_artifacts.append(
            {
                "artifact_key": art.artifact_key,
                "artifact_type": art.artifact_type,
                "module_key": art.module_key,
                "metric_keys": art.metric_keys,
                "status": art.status,
                "annotation_frame": art.annotation_frame,
                "source_video_frame": art.source_video_frame,
                "frame_range": art.annotation_frame_range,
                "storage_path": art.storage_path,
                "url": public_asset_url(art.storage_path) if art.storage_path else None,
                "mime_type": art.mime_type,
                "width": art.width,
                "height": art.height,
                "checksum_sha256": art.checksum_sha256,
                "source_annotation_revision": artifact_set.source_annotation_revision,
                "generator_version": GENERATOR_VERSION,
                "status_detail": art.status,
                "skip_reason": art.skip_reason,
                "metadata": art.artifact_metadata,
                "presentation": _presentation(art),
            }
        )
    return {
        "schema_version": "swim-kinematic-artifacts.v1",
        "artifact_set_id": artifact_set.id,
        "annotation_metric_id": artifact_set.annotation_metric_id,
        "normalized_annotation_id": artifact_set.normalized_annotation_id,
        "source_annotation_revision": artifact_set.source_annotation_revision,
        "source_metric": {
            "schema_version": metric.schema_version,
            "calculator": metric.calculator,
            "calculator_version": metric.calculator_version,
            "hash": artifact_set.source_metric_hash,
        },
        "generator": {
            "name": GENERATOR_NAME,
            "version": GENERATOR_VERSION,
            "style_profile": STYLE_PROFILE,
        },
        "status": artifact_set.status,
        "created_at": artifact_set.created_at.isoformat() if artifact_set.created_at else None,
        "artifacts": out_artifacts,
        "warnings": artifact_set.warnings,
        "radar": {
            "semantics": "within_clip_visualization_only",
            "overall_score": None,
            "disclaimer": "仅用于当前片段内部运动稳定性展示，不代表经过验证的综合技术评分。",
            "index_method_version": "stability-display-index.v1",
            "config_hash": config_hash(),
        },
    }


def project_to_report_assets(artifact_set: KinematicArtifactSet) -> list[dict]:
    """Convert persisted artifacts into the existing front-end ReportAsset shape."""
    assets = []
    for art in artifact_set.artifacts:
        if art.status != "ready" or not art.storage_path:
            continue
        assets.append(
            {
                "key": art.artifact_key,
                "type": "annotated_frame" if art.artifact_type == "annotated_keyframe" else "image",
                "title": (art.artifact_metadata or {}).get("value") or art.artifact_key,
                "url": public_asset_url(art.storage_path),
                "label": art.artifact_key,
                "value": (art.artifact_metadata or {}).get("value"),
                "caption": "基于二维骨架几何的客观指标。",
            }
        )
    return assets
