import json
from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.annotation import AnnotationFile, AnnotationFileStatus, AnnotationSource
from app.models.normalized_annotation import NormalizedAnnotation
from app.repositories.annotation_repository import get_with_ownership_check
from app.repositories.normalized_annotation_repository import get_by_annotation_file
from app.schemas.normalized_annotation import (
    AnnotationQuality,
    NormalizedAnnotationCreate,
    ParseSummary,
)
from app.services.annotation_quality.legacy import normalize_quality_payload
from app.services.annotation_quality.validator import AnnotationQualityValidator
from app.services.annotation_quality.provider import YamlQualityProfileProvider
from app.services.parsers import (
    KinoveaParseError,
    build_parse_summary,
    parse_kinovea_annotation,
)

import os


def _get_validator() -> AnnotationQualityValidator:
    profiles_dir = os.path.join(os.path.dirname(__file__), "annotation_quality", "profiles")
    provider = YamlQualityProfileProvider(profiles_dir)
    return AnnotationQualityValidator(profile_provider=provider)


def update_annotation_file_status(
    db: Session, annotation_file: AnnotationFile, success: bool, error_message: str | None = None
) -> None:
    if success:
        annotation_file.status = AnnotationFileStatus.PARSED
        annotation_file.parse_error = None
    else:
        annotation_file.status = AnnotationFileStatus.PARSE_FAILED
        annotation_file.parse_error = error_message or "解析失败"
    db.add(annotation_file)
    db.commit()


def create_normalized_annotation(
    db: Session,
    *,
    session_video_id: int,
    data: NormalizedAnnotationCreate,
    created_by: int,
) -> NormalizedAnnotation:
    validator = _get_validator()
    session_video = db.get(type(data), session_video_id) if hasattr(data, 'id') else None
    video_fps = float(session_video.fps) if session_video and hasattr(session_video, 'fps') and session_video.fps else None
    quality_report = validator.validate(
        events=[e.model_dump() for e in data.events],
        keypoint_frames=[k.model_dump() for k in data.keypoint_frames],
        scale=data.scale.model_dump() if data.scale else None,
        fps=data.fps,
        frame_count=data.frame_count,
        reference_lines=data.reference_lines,
        swim_direction=data.swim_direction,
        video_fps=video_fps,
    )
    quality = quality_report.model_dump(mode="json")

    ann = NormalizedAnnotation(
        session_video_id=session_video_id,
        annotation_file_id=data.annotation_file_id,
        source=data.source.value,
        fps=data.fps,
        frame_count=data.frame_count,
        duration_sec=data.duration_sec,
        scale=data.scale.model_dump() if data.scale else None,
        coordinate_system=data.coordinate_system.model_dump(),
        events=[e.model_dump() for e in data.events],
        keypoint_frames=[k.model_dump() for k in data.keypoint_frames],
        trajectories=[t.model_dump() for t in data.trajectories],
        manual_tags=[t.model_dump() for t in data.manual_tags],
        reference_lines=data.reference_lines,
        distance_markers=data.distance_markers,
        swim_direction=data.swim_direction,
        quality=quality,
        created_by=created_by,
    )
    db.add(ann)
    db.commit()
    db.refresh(ann)
    return ann


@dataclass
class ParseAnnotationResult:
    annotation: NormalizedAnnotation
    summary: ParseSummary
    warnings: list[str]


def parse_annotation_file(
    db: Session,
    annotation_file_id: int,
    current_user_id: int,
) -> ParseAnnotationResult:
    ann_file = get_with_ownership_check(db, annotation_file_id, current_user_id)
    source_value = getattr(ann_file.source, "value", str(ann_file.source))

    def _fail(exc: Exception, status_code: int = 400) -> None:
        update_annotation_file_status(db, ann_file, success=False, error_message=str(exc))
        raise HTTPException(status_code=status_code, detail=f"标注文件解析失败: {exc}")

    parsed = None
    raw = None
    try:
        if source_value == AnnotationSource.KINOVEA.value:
            fallback_fps = float(ann_file.annotation_fps) if ann_file.annotation_fps else None
            parsed = parse_kinovea_annotation(
                ann_file.storage_path,
                file_type=ann_file.file_type or "json",
                fallback_fps=fallback_fps,
            )
            fps = parsed.fps or fallback_fps or float(ann_file.annotation_fps or 60)
            events = [e.model_dump() for e in parsed.events]
            keypoint_frames = [k.model_dump() for k in parsed.keypoint_frames]
            trajectories = [t.model_dump() for t in parsed.trajectories]
            manual_tags = [m.model_dump() for m in parsed.manual_tags]
            scale = parsed.scale.model_dump() if parsed.scale else None
            coordinate_system = parsed.coordinate_system.model_dump()
            frame_count = parsed.frame_count or (int(ann_file.frame_count) if ann_file.frame_count else None)
            duration_sec = parsed.duration_sec or (float(ann_file.duration_sec) if ann_file.duration_sec else None)
        else:
            with open(ann_file.storage_path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            fps = raw.get("fps", float(ann_file.annotation_fps or 60))
            events = raw.get("events", [])
            keypoint_frames = raw.get("keypoint_frames", [])
            trajectories = raw.get("trajectories", [])
            manual_tags = raw.get("manual_tags", [])
            scale = raw.get("scale")
            coordinate_system = raw.get("coordinate_system", {})
            frame_count = raw.get("frame_count") or raw.get("video", {}).get("frame_count")
            duration_sec = raw.get("duration_sec") or raw.get("video", {}).get("duration_sec")
    except KinoveaParseError as exc:
        _fail(exc)
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        _fail(exc)

    # ── quality v2 ──
    session_video = ann_file.session_video
    video_fps = float(session_video.fps) if session_video and hasattr(session_video, 'fps') and session_video.fps else None
    video_width = session_video.video_file.width if session_video and hasattr(session_video, 'video_file') and session_video.video_file else None
    video_height = session_video.video_file.height if session_video and hasattr(session_video, 'video_file') and session_video.video_file else None

    validator = _get_validator()
    quality_report = validator.validate(
        events=events,
        keypoint_frames=keypoint_frames,
        scale=scale,
        fps=fps,
        frame_count=frame_count,
        reference_lines=raw.get("reference_lines") if raw else None,
        swim_direction=raw.get("swim_direction") if raw else None,
        video_fps=video_fps,
        video_width=video_width,
        video_height=video_height,
        view_type=str(session_video.view_type.value) if session_video and hasattr(session_video, 'view_type') else None,
    )
    quality = quality_report.model_dump(mode="json")

    # ── upsert ──
    metadata = parsed.model_dump() if parsed is not None else (raw.get("metadata", {}) if raw else {})
    existing = get_by_annotation_file(db, annotation_file_id)
    if existing:
        existing.revision += 1
        existing.source = source_value
        existing.fps = fps
        existing.frame_count = frame_count
        existing.duration_sec = duration_sec
        existing.scale = scale
        existing.coordinate_system = coordinate_system
        existing.events = events
        existing.keypoint_frames = keypoint_frames
        existing.trajectories = trajectories
        existing.manual_tags = manual_tags
        existing.reference_lines = raw.get("reference_lines") if raw else None
        existing.distance_markers = raw.get("distance_markers") if raw else None
        existing.swim_direction = raw.get("swim_direction") if raw else None
        existing.quality = quality
        existing.annotation_metadata = metadata
        ann = existing
        db.add(ann)
    else:
        ann = NormalizedAnnotation(
            session_video_id=ann_file.session_video_id,
            annotation_file_id=annotation_file_id,
            source=source_value,
            fps=fps,
            frame_count=frame_count,
            duration_sec=duration_sec,
            scale=scale,
            coordinate_system=coordinate_system,
            events=events,
            keypoint_frames=keypoint_frames,
            trajectories=trajectories,
            manual_tags=manual_tags,
            quality=quality,
            annotation_metadata=metadata,
            created_by=current_user_id,
        )
        db.add(ann)

    db.commit()
    db.refresh(ann)

    update_annotation_file_status(db, ann_file, success=True)

    summary = build_parse_summary(parsed) if parsed is not None else ParseSummary(
        events_count=len(events),
        keypoint_frames_count=len(keypoint_frames),
        trajectories_count=len(trajectories),
        manual_tags_count=len(manual_tags),
    )
    warnings = parsed.warnings if parsed is not None else []
    return ParseAnnotationResult(annotation=ann, summary=summary, warnings=warnings)
