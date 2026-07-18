"""Deterministic generation signature and canonical JSON hashing."""

import hashlib
import json


def canonical_json(payload: dict) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def metric_hash(metrics: dict) -> str:
    payload = {
        "summary": metrics.get("summary", {}),
        "time_series": metrics.get("time_series", {}),
        "ranges": metrics.get("ranges", {}),
        "representative_frames": metrics.get("representative_frames", {}),
    }
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def generation_signature(
    *,
    annotation_metric_id: int,
    source_annotation_revision: int,
    source_metric_hash: str,
    source_video_checksum: str | None,
    generator_version: str,
    artifact_plan_version: str,
    style_profile: str,
    style_profile_hash: str,
    stability_index_config_hash: str,
) -> str:
    payload = {
        "annotation_metric_id": annotation_metric_id,
        "source_annotation_revision": source_annotation_revision,
        "source_metric_hash": source_metric_hash,
        "source_video_checksum": source_video_checksum,
        "generator_version": generator_version,
        "artifact_plan_version": artifact_plan_version,
        "style_profile": style_profile,
        "style_profile_hash": style_profile_hash,
        "stability_index_config_hash": stability_index_config_hash,
    }
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
