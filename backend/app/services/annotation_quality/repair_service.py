import math
import os
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.normalized_annotation import NormalizedAnnotation
from app.schemas.normalized_annotation import QualityRepairPayload
from app.services.annotation_quality.profile_resolver import resolve_quality_profile_id
from app.services.annotation_quality.readiness import derive_analysis_readiness
from app.services.annotation_quality.validator import AnnotationQualityValidator
from app.services.annotation_quality.provider import YamlQualityProfileProvider


def _validator() -> AnnotationQualityValidator:
    profiles_dir = os.path.join(os.path.dirname(__file__), "profiles")
    return AnnotationQualityValidator(
        profile_provider=YamlQualityProfileProvider(profiles_dir)
    )


def _video_dimensions(annotation: NormalizedAnnotation) -> tuple[int | None, int | None]:
    resolution = getattr(annotation.session_video, "resolution", None)
    if not resolution or "x" not in str(resolution):
        return None, None
    try:
        width, height = (int(value) for value in str(resolution).split("x", 1))
        return width, height
    except ValueError:
        return None, None


def _validate_points(points: list[Any], width: int | None, height: int | None) -> list[list[float]]:
    if len(points) != 2:
        raise HTTPException(status_code=422, detail="必须提供两个参考点")
    normalized: list[list[float]] = []
    for point in points:
        x = float(point.x)
        y = float(point.y)
        if not math.isfinite(x) or not math.isfinite(y):
            raise HTTPException(status_code=422, detail="参考点坐标必须是有限数值")
        if width is not None and not 0 <= x < width:
            raise HTTPException(status_code=422, detail="参考点 X 坐标超出视频范围")
        if height is not None and not 0 <= y < height:
            raise HTTPException(status_code=422, detail="参考点 Y 坐标超出视频范围")
        normalized.append([x, y])
    if normalized[0] == normalized[1]:
        raise HTTPException(status_code=422, detail="两个参考点不能重合")
    return normalized


def _merge_events(existing: list[dict], additions: list[Any]) -> list[dict]:
    events = [deepcopy(event) for event in existing if isinstance(event, dict)]
    seen = {
        (event.get("name"), event.get("frame"), event.get("side", "unknown"))
        for event in events
    }
    for event in additions:
        key = (event.name, event.frame, event.side)
        if key in seen:
            continue
        events.append({
            "name": event.name,
            "label": event.label or event.name,
            "frame": event.frame,
            "time_sec": event.time_sec,
            "side": event.side,
            "confidence": event.confidence,
            "labeled_by": "manual",
        })
        seen.add(key)
    return sorted(events, key=lambda event: (event.get("frame", 0), event.get("name", "")))


def _build_frame_mapping(override: Any, fps: float | None) -> dict[str, Any]:
    if override.mode == "affine":
        if override.source_frame_stride is None or override.source_frame_stride <= 0:
            raise HTTPException(status_code=422, detail="affine 帧映射的 stride 必须为正数")
        if override.source_frame_offset is None:
            raise HTTPException(status_code=422, detail="affine 帧映射必须提供 offset")
    return {
        "mode": override.mode,
        "verified": bool(override.confirmed),
        "verification_reason": "user_confirmed" if override.confirmed else "user_provided_not_confirmed",
        "source_frame_offset": override.source_frame_offset,
        "source_frame_stride": override.source_frame_stride,
        "video_fps": fps,
    }


def apply_quality_repair(
    db: Session,
    annotation: NormalizedAnnotation,
    payload: QualityRepairPayload,
) -> dict[str, Any]:
    if payload.expected_revision != annotation.revision:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "ANNOTATION_REVISION_CONFLICT",
                "message": "标注已被其他操作更新，请刷新后重试。",
                "current_revision": annotation.revision,
            },
        )

    width, height = _video_dimensions(annotation)
    scale = deepcopy(annotation.scale) if annotation.scale else None
    reference_lines = deepcopy(annotation.reference_lines) if annotation.reference_lines else {}
    events = list(annotation.events or [])
    metadata = deepcopy(annotation.annotation_metadata or {})

    if payload.scale is not None:
        points = _validate_points(payload.scale.points, width, height)
        dx = points[1][0] - points[0][0]
        dy = points[1][1] - points[0][1]
        pixel_length = math.hypot(dx, dy)
        scale = {
            "method": payload.scale.method,
            "pixels_per_meter": pixel_length / payload.scale.reference_length_m,
            "reference_length_m": payload.scale.reference_length_m,
            "reference_points": points,
            "confidence": payload.scale.confidence,
            "note": payload.scale.note,
        }

    if payload.waterline is not None:
        points = _validate_points(payload.waterline.points, width, height)
        reference_lines["waterline"] = {
            "points": points,
            "confidence": payload.waterline.confidence,
        }

    if payload.swim_direction is not None:
        annotation.swim_direction = payload.swim_direction

    if payload.events:
        events = _merge_events(events, payload.events)

    if payload.frame_mapping is not None:
        mapping = _build_frame_mapping(
            payload.frame_mapping,
            float(annotation.fps) if annotation.fps else None,
        )
        metadata["frame_mapping"] = mapping

    new_revision = annotation.revision + 1
    annotation.revision = new_revision
    annotation.scale = scale
    annotation.reference_lines = reference_lines or None
    annotation.events = events
    annotation.quality = {}
    metadata.setdefault("repairs", []).append({
        "revision": new_revision,
        "at": datetime.now(timezone.utc).isoformat(),
        "fields": [
            field for field, value in (
                ("scale", payload.scale),
                ("waterline", payload.waterline),
                ("swim_direction", payload.swim_direction),
                ("events", payload.events),
                ("frame_mapping", payload.frame_mapping),
            ) if value is not None
        ],
    })
    annotation.annotation_metadata = metadata

    video_metadata = metadata.get("video")
    frame_mapping = metadata.get("frame_mapping")
    profile_id = resolve_quality_profile_id(annotation.source)
    report = _validator().validate(
        events=events,
        keypoint_frames=annotation.keypoint_frames or [],
        scale=scale,
        fps=float(annotation.fps) if annotation.fps else None,
        frame_count=annotation.frame_count,
        reference_lines=annotation.reference_lines,
        swim_direction=annotation.swim_direction,
        video_fps=float(annotation.session_video.fps) if annotation.session_video and annotation.session_video.fps else None,
        video_width=width,
        video_height=height,
        view_type=str(annotation.session_video.view_type.value) if annotation.session_video and hasattr(annotation.session_video.view_type, "value") else str(annotation.session_video.view_type) if annotation.session_video else None,
        profile_id=profile_id,
        source_revision=new_revision,
        frame_mapping=frame_mapping,
        video_metadata=video_metadata,
    )
    annotation.quality = report.model_dump(mode="json")
    db.add(annotation)
    db.commit()
    db.refresh(annotation)
    return {
        "normalized_annotation_id": annotation.id,
        "revision": annotation.revision,
        "quality": report,
        "analysis_readiness": derive_analysis_readiness(annotation.quality),
        "module_readiness": annotation.quality.get("module_readiness", {}),
    }
