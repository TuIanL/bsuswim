"""Kinematic artifact generation service.

Orchestrates: preflight → plan → select keyframes → extract video frames →
render PNG/SVG → persist ArtifactSet + Artifact rows → build immutable manifest.
"""

import asyncio
import hashlib
import json
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.annotation_metric import AnnotationMetric
from app.models.kinematic_artifact import KinematicArtifact, KinematicArtifactSet
from app.models.normalized_annotation import NormalizedAnnotation
from app.models.video import SessionVideo, VideoFile
from app.services.kinematic_artifacts import stability_index
from app.services.kinematic_artifacts.chart_renderers import (
    render_angle_timeseries,
    render_range_comparison,
    render_stability_radar,
    render_trajectory_chart,
)
from app.services.kinematic_artifacts.constants import (
    ARTIFACT_KEYS,
    ARTIFACT_METRIC_KEYS,
    ArtifactSetStatus,
    ArtifactStatus,
    ArtifactType,
    GENERATOR_NAME,
    GENERATOR_VERSION,
    SCHEMA_VERSION,
    SkipReason,
    STYLE_PROFILE,
    ARTIFACT_PLAN_VERSION,
    KEYFRAME_WIDTH,
    KEYFRAME_HEIGHT,
)
from app.services.kinematic_artifacts.frame_provider import KinematicFrameSequenceProvider
from app.services.kinematic_artifacts.frame_selection import select_all_keyframes
from app.services.kinematic_artifacts.keyframe_renderer import render_keyframe
from app.services.kinematic_artifacts.signature import generation_signature, metric_hash
from app.services.metrics.kinematics.frame_resolver import resolve_frames
from app.services.storage import StorageService, public_asset_url

SUPPORTED_CALCULATOR = "side_2d_kinematics"
SUPPORTED_SCHEMA = "swim-side-kinematics.v1"


def _style_profile_hash() -> str:
    payload = {
        "style_profile": STYLE_PROFILE,
        "keyframe_w": KEYFRAME_WIDTH,
        "keyframe_h": KEYFRAME_HEIGHT,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


class GenerationError(Exception):
    def __init__(self, code: str, status_code: int = 400, message: str = ""):
        self.code = code
        self.status_code = status_code
        self.message = message
        super().__init__(message or code)


def _preflight(db: Session, annotation_metric_id: int):
    metric = db.get(AnnotationMetric, annotation_metric_id)
    if metric is None:
        raise GenerationError("metric_unavailable", 404)
    if metric.calculator != SUPPORTED_CALCULATOR or metric.schema_version != SUPPORTED_SCHEMA:
        raise GenerationError("unsupported_artifact_metric_schema", 422)
    if metric.source_revision is None:
        raise GenerationError("metric_revision_stale", 422, "source_revision missing")
    annotation = db.get(NormalizedAnnotation, metric.normalized_annotation_id)
    if annotation is None:
        raise GenerationError("metric_unavailable", 404)
    if metric.source_revision != annotation.revision:
        raise GenerationError("metric_revision_stale", 409)
    session_video = db.get(SessionVideo, metric.session_video_id) if metric.session_video_id else None
    video_file = None
    if session_video is not None:
        video_file = db.get(VideoFile, session_video.video_file_id)
    return metric, annotation, session_video, video_file


def _plan_artifacts() -> list[tuple[str, str, ArtifactType]]:
    out = []
    for module_key, items in ARTIFACT_KEYS.items():
        for key, atype in items:
            out.append((key, module_key, atype))
    return out


def generate(
    db: Session,
    annotation_metric_id: int,
    *,
    force: bool = False,
    current_user_id: int | None = None,
) -> tuple[KinematicArtifactSet, bool]:
    metric, annotation, session_video, video_file = _preflight(db, annotation_metric_id)

    mhash = metric_hash(metric.metrics)
    video_checksum = video_file.checksum_sha256 if video_file else None
    sig = generation_signature(
        annotation_metric_id=annotation_metric_id,
        source_annotation_revision=metric.source_revision,
        source_metric_hash=mhash,
        source_video_checksum=video_checksum,
        generator_version=GENERATOR_VERSION,
        artifact_plan_version=ARTIFACT_PLAN_VERSION,
        style_profile=STYLE_PROFILE,
        style_profile_hash=_style_profile_hash(),
        stability_index_config_hash=stability_index.config_hash(),
    )

    existing = (
        db.query(KinematicArtifactSet)
        .filter_by(annotation_metric_id=annotation_metric_id, generation_signature=sig)
        .with_for_update()
        .first()
    )
    if existing is not None and not force:
        return existing, False
    if existing is not None and force:
        # in-place regeneration: reset to generating, keep prior files until finalize
        existing.status = ArtifactSetStatus.GENERATING
        db.flush()
        artifact_set = existing
    else:
        artifact_set = KinematicArtifactSet(
            annotation_metric_id=annotation_metric_id,
            normalized_annotation_id=annotation.id,
            session_video_id=metric.session_video_id,
            source_annotation_revision=metric.source_revision,
            source_metric_schema_version=metric.schema_version,
            source_metric_calculator=metric.calculator,
            source_metric_calculator_version=metric.calculator_version,
            source_metric_hash=mhash,
            generation_signature=sig,
            status=ArtifactSetStatus.GENERATING,
            created_by=current_user_id,
        )
        db.add(artifact_set)
        db.flush()

    try:
        _render_all(db, artifact_set, metric, annotation, session_video, video_file, video_checksum)
    except Exception:  # systemic failure preserved
        db.rollback()
        artifact_set = db.get(KinematicArtifactSet, artifact_set.id)
        artifact_set.status = ArtifactSetStatus.FAILED
        artifact_set.warnings.append("systemic_generation_error")
        db.commit()
        raise

    db.commit()
    return artifact_set, existing is None


def _render_all(db, artifact_set, metric, annotation, session_video, video_file, video_checksum):
    storage = StorageService()
    summary = metric.metrics.get("summary", {})
    time_series = metric.metrics.get("time_series", {})
    ranges = metric.metrics.get("ranges", {})
    frames = resolve_frames(annotation.keypoint_frames or [])
    provider = KinematicFrameSequenceProvider()
    canonical = provider.build(annotation)

    ref_body = metric.metrics.get("reference_body_length", {})
    ref_px = ref_body.get("value_px") if isinstance(ref_body, dict) else None

    selected = select_all_keyframes(summary, time_series, canonical, ref_px)
    selected_by_key = {s.artifact_metric_key: s for s in selected}

    mapping = (annotation.annotation_metadata or {}).get("frame_mapping", {})
    mapping_verified = bool(mapping.get("verified")) if isinstance(mapping, dict) else False

    base_dir = (
        f"kinematic-artifacts/{metric.id}/r{metric.source_revision}/{artifact_set.generation_signature[:12]}"
    )
    warnings: list[str] = []

    artifacts: list[KinematicArtifact] = []
    extracted: dict[int, Any] = {}

    # --- keyframes (require verified mapping + video) ---
    if mapping_verified and video_file is not None:
        from app.services.kinematic_artifacts.video_extractor import VideoFrameExtractor

        try:
            extractor = VideoFrameExtractor(video_file.storage_path)
        except FileNotFoundError:
            extractor = None
            warnings.append(SkipReason.SOURCE_VIDEO_MISSING)
        if extractor:
            needed = [s.source_video_frame for s in selected if s.source_video_frame is not None]
            try:
                extracted = extractor.extract_many(needed)
            except Exception:
                extracted = {}
                warnings.append(SkipReason.VIDEO_DECODE_FAILED)
            extractor.close()
    elif video_file is None:
        warnings.append(SkipReason.SOURCE_VIDEO_MISSING)
    else:
        warnings.append(SkipReason.FRAME_MAPPING_UNVERIFIED)

    for key, module_key, atype in _plan_artifacts():
        if atype == ArtifactType.ANNOTATED_KEYFRAME:
            artifacts.append(
                _render_keyframe(
                    storage, base_dir, key, module_key, selected_by_key, canonical, extracted, ref_px,
                )
            )
        elif atype == ArtifactType.TIME_SERIES_CHART:
            artifacts.append(_render_timeseries(storage, base_dir, key, module_key, time_series))
        elif atype == ArtifactType.TRAJECTORY_CHART:
            artifacts.append(_render_trajectory(storage, base_dir, key, module_key, canonical, ref_px))
        elif atype == ArtifactType.RANGE_CHART:
            artifacts.append(_render_range(storage, base_dir, key, module_key, summary, ranges))
        elif atype == ArtifactType.RADAR_CHART:
            artifacts.append(_render_radar(storage, base_dir, key, module_key, summary, time_series))

    # finalize
    db.query(KinematicArtifact).filter_by(artifact_set_id=artifact_set.id).delete()
    db.flush()
    for a in artifacts:
        a.artifact_set_id = artifact_set.id
        db.add(a)
    db.flush()

    ready = sum(1 for a in artifacts if a.status == ArtifactStatus.READY)
    if ready == 0:
        artifact_set.status = ArtifactSetStatus.FAILED
    elif all(a.status == ArtifactStatus.READY for a in artifacts):
        artifact_set.status = ArtifactSetStatus.READY
    else:
        artifact_set.status = ArtifactSetStatus.PARTIAL
    artifact_set.warnings = warnings
    _build_manifest(artifact_set, artifacts, metric, video_checksum)


def _store(storage: StorageService, base_dir: str, key: str, ext: str, data: bytes, mime: str) -> dict:
    rel = f"{base_dir}/{key}.{ext}"
    return asyncio.run(storage.save_bytes(data, rel, content_type=mime))


def _render_keyframe(storage, base_dir, key, module_key, selected_by_key, canonical, extracted, ref_px):
    sel = selected_by_key.get(key)
    art = KinematicArtifact(
        artifact_key=key, artifact_type=ArtifactType.ANNOTATED_KEYFRAME, module_key=module_key,
        metric_keys=ARTIFACT_METRIC_KEYS.get(key, []), status=ArtifactStatus.SKIPPED,
    )
    if sel is None or sel.source_video_frame is None:
        art.skip_reason = SkipReason.FRAME_MAPPING_UNVERIFIED
        return art
    ef = extracted.get(sel.source_video_frame)
    if ef is None:
        art.skip_reason = SkipReason.VIDEO_DECODE_FAILED
        return art
    if not ef.exact_match:
        art.skip_reason = SkipReason.VIDEO_DECODE_FAILED
        art.artifact_metadata = {"requested_frame": ef.requested_frame, "decoded_frame": ef.decoded_frame}
        return art
    frame = next((f for f in canonical if f.annotation_frame == sel.annotation_frame), None)
    if frame is None:
        art.skip_reason = SkipReason.SOURCE_FRAME_MISSING
        return art
    try:
        img = render_keyframe(ef.image, frame, reference_basis_label="相对画面水平线",
                              value_label=f"{key.split('.')[-1]}")
    except ValueError:
        art.skip_reason = SkipReason.COORDINATE_SPACE_MISMATCH
        return art
    res = _store(storage, base_dir, key, "png", _img_bytes(img), "image/png")
    art.status = ArtifactStatus.READY
    art.annotation_frame = sel.annotation_frame
    art.source_video_frame = sel.source_video_frame
    art.storage_path = res["relative_path"]
    art.mime_type = "image/png"
    art.width = img.shape[1]
    art.height = img.shape[0]
    art.size_bytes = res["size_bytes"]
    art.checksum_sha256 = res["checksum_sha256"]
    art.artifact_metadata = sel.metadata or {}
    return art


def _img_bytes(img) -> bytes:
    import cv2

    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise RuntimeError("imencode failed")
    return buf.tobytes()


def _render_timeseries(storage, base_dir, key, module_key, time_series):
    art = KinematicArtifact(
        artifact_key=key, artifact_type=ArtifactType.TIME_SERIES_CHART, module_key=module_key,
        metric_keys=ARTIFACT_METRIC_KEYS.get(key, []), status=ArtifactStatus.READY,
    )
    metric_keys = {
        "body_posture.chart.angle_timeseries": ["torso_axis_angle_deg", "body_axis_angle_deg"],
        "upper_limb.chart.elbow_angle_timeseries": ["left_elbow_angle_deg", "right_elbow_angle_deg"],
        "lower_limb.chart.knee_angle_timeseries": ["left_knee_angle_deg", "right_knee_angle_deg"],
    }[key]
    series = {mk: time_series.get(mk, []) for mk in metric_keys}
    svg = render_angle_timeseries(series, title=key)
    res = _store(storage, base_dir, key, "svg", svg, "image/svg+xml")
    art.storage_path = res["relative_path"]
    art.mime_type = "image/svg+xml"
    art.width = 1200
    art.height = 675
    art.size_bytes = res["size_bytes"]
    art.checksum_sha256 = res["checksum_sha256"]
    return art


def _render_trajectory(storage, base_dir, key, module_key, canonical, ref_px):
    from app.services.kinematic_artifacts.constants import MAX_TRAJECTORY_POINTS

    art = KinematicArtifact(
        artifact_key=key, artifact_type=ArtifactType.TRAJECTORY_CHART, module_key=module_key,
        metric_keys=ARTIFACT_METRIC_KEYS.get(key, []), status=ArtifactStatus.READY,
    )
    trajectories: dict[str, list] = {}
    if key == "upper_limb.chart.joint_trajectories":
        trajectories = _limb_trajectories(canonical, ["left", "right"], "wrist", "elbow", ref_px)
    elif key == "lower_limb.chart.joint_trajectories":
        trajectories = _lower_trajectories(canonical, ref_px)
    elif key == "body_posture.chart.hip_trajectory":
        trajectories = _hip_trajectory(canonical, ref_px)
    unit = "body length ratio" if ref_px else "px"
    svg = render_trajectory_chart(trajectories, title=key, unit=unit)
    res = _store(storage, base_dir, key, "svg", svg, "image/svg+xml")
    art.storage_path = res["relative_path"]
    art.mime_type = "image/svg+xml"
    art.width = 1200
    art.height = 675
    art.size_bytes = res["size_bytes"]
    art.checksum_sha256 = res["checksum_sha256"]
    art.artifact_metadata = {"unit": unit, "reference_body_length_px": ref_px}
    return art


def _pt(p):
    return None if p is None or not p.available or p.x is None else (p.x, p.y)


def _rel_series(canonical, target_side_joint, anchor_side_joint, ref_px):
    out = []
    anchor0 = None
    for f in canonical:
        t = f.points.get(target_side_joint)
        a = f.points.get(anchor_side_joint)
        tp, ap = _pt(t), _pt(a)
        if tp is None or ap is None:
            out.append((f.annotation_frame, None, None))
            continue
        rx, ry = tp[0] - ap[0], -(tp[1] - ap[1])
        if ref_px:
            rx, ry = rx / ref_px, ry / ref_px
        out.append((f.annotation_frame, rx, ry))
    return out


def _limb_trajectories(canonical, sides, wrist, elbow, ref_px):
    traj = {}
    for side in sides:
        traj[f"{side}_{wrist}"] = _rel_series(canonical, f"{side}_{wrist}", f"{side}_shoulder", ref_px)
        traj[f"{side}_{elbow}"] = _rel_series(canonical, f"{side}_elbow", f"{side}_shoulder", ref_px)
    return traj


def _lower_trajectories(canonical, ref_px):
    traj = {}
    for side in ("left", "right"):
        traj[f"{side}_knee"] = _rel_series(canonical, f"{side}_knee", "hip_mid", ref_px)
        traj[f"{side}_ankle"] = _rel_series(canonical, f"{side}_ankle", "hip_mid", ref_px)
    return traj


def _hip_trajectory(canonical, ref_px):
    out = []
    first = None
    for f in canonical:
        hp = _pt(f.hip_mid)
        if hp is None:
            out.append((f.annotation_frame, None, None))
            continue
        if first is None:
            first = hp
        rx, ry = hp[0] - first[0], -(hp[1] - first[1])
        if ref_px:
            rx, ry = rx / ref_px, ry / ref_px
        out.append((f.annotation_frame, rx, ry))
    return {"hip_mid": out}


def _render_range(storage, base_dir, key, module_key, summary, ranges):
    art = KinematicArtifact(
        artifact_key=key, artifact_type=ArtifactType.RANGE_CHART, module_key=module_key,
        metric_keys=ARTIFACT_METRIC_KEYS.get(key, []), status=ArtifactStatus.READY,
    )
    panels = {
        "Joint ROM (deg)": {
            "left_elbow": _env(summary, "elbow_rom_deg", "left") or 0,
            "right_elbow": _env(summary, "elbow_rom_deg", "right") or 0,
            "left_knee": _env(summary, "knee_rom_deg", "left") or 0,
            "right_knee": _env(summary, "knee_rom_deg", "right") or 0,
        },
        "Vertical excursion": {
            "head": _env_val(summary, "head_vertical_range_px") or 0,
            "hip": _env_val(summary, "hip_vertical_range_px") or 0,
        },
        "Body axis range (deg)": {
            "P05": _range_val(ranges, "body_axis_angle_deg", "p05") or 0,
            "P95": _range_val(ranges, "body_axis_angle_deg", "p95") or 0,
            "range": _range_val(ranges, "body_axis_angle_deg", "range") or 0,
        },
    }
    svg = render_range_comparison(panels)
    res = _store(storage, base_dir, key, "svg", svg, "image/svg+xml")
    art.storage_path = res["relative_path"]
    art.mime_type = "image/svg+xml"
    art.width = 1200
    art.height = 675
    art.size_bytes = res["size_bytes"]
    art.checksum_sha256 = res["checksum_sha256"]
    return art


def _env(summary, key, side_prefix=None):
    env = summary.get(key)
    if not isinstance(env, dict):
        return None
    val = env.get("value")
    if isinstance(val, dict):
        return val.get(side_prefix)
    return val


def _env_val(summary, key):
    env = summary.get(key)
    if isinstance(env, dict):
        return env.get("value")
    return None


def _range_val(ranges, key, sub):
    r = ranges.get(key)
    if isinstance(r, dict):
        return r.get(sub)
    return None


def _render_radar(storage, base_dir, key, module_key, summary, time_series):
    art = KinematicArtifact(
        artifact_key=key, artifact_type=ArtifactType.RADAR_CHART, module_key=module_key,
        metric_keys=ARTIFACT_METRIC_KEYS.get(key, []), status=ArtifactStatus.READY,
    )
    raw_inputs = _radar_inputs(summary, time_series)
    axes = stability_index.compute_axes(raw_inputs)
    if stability_index.available_axis_count(axes) < 3:
        art.status = ArtifactStatus.SKIPPED
        art.skip_reason = SkipReason.RADAR_INPUTS_INSUFFICIENT
        return art
    svg = render_stability_radar(axes, title="当前片段运动稳定性概览")
    res = _store(storage, base_dir, key, "svg", svg, "image/svg+xml")
    art.storage_path = res["relative_path"]
    art.mime_type = "image/svg+xml"
    art.width = 900
    art.height = 900
    art.size_bytes = res["size_bytes"]
    art.checksum_sha256 = res["checksum_sha256"]
    art.artifact_metadata = {"axes": axes}
    return art


def _radar_inputs(summary, time_series):
    return {
        "body_posture": {
            "posture_stability_cv": _env_val(summary, "posture_stability_cv") or 0,
            "body_angle_std_deg": _env_val(summary, "body_angle_std_deg") or 0,
        },
        "lower_limb_rhythm": {
            "kick_periodicity_score": (_env_val(summary, "kick_periodicity") or {}).get("score")
            if isinstance(_env_val(summary, "kick_periodicity"), dict) else None,
            "continuity_factor": (_env_val(summary, "kick_periodicity") or {}).get("continuity_factor"),
        },
        "head_control": {
            "trunk_vertical_stability": _env_val(summary, "trunk_vertical_stability") or 0,
        },
        "data_completeness": {
            "valid_keypoint_ratio": 1.0,
            "available_metric_ratio": 1.0,
            "mapping_verified": 1,
        },
    }


def _build_manifest(artifact_set, artifacts, metric, video_checksum):
    from app.services.kinematic_artifacts.schemas_api import build_manifest_payload

    payload = build_manifest_payload(artifact_set, artifacts, metric, video_checksum)
    artifact_set.manifest = payload
    artifact_set.manifest_sha256 = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()
    ).hexdigest()
