import json
import os
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
    ParseAnnotationOptions,
    ParseSummary,
    build_contiguous_frame_ranges,
)
from app.services.annotation_derivation.builder import AnnotationDerivedDataBuilder
from app.services.annotation_quality.legacy import normalize_quality_payload
from app.services.annotation_quality.profile_resolver import resolve_quality_profile_id
from app.services.annotation_quality.validator import AnnotationQualityValidator
from app.services.annotation_quality.provider import YamlQualityProfileProvider
from app.services.parsers import (
    CvatParseError,
    CvatAnnotationNormalizer,
    FrameMapping,
    FrameMappingResolver,
    KinoveaParseError,
    build_parse_summary,
    parse_cvat_xml,
    parse_kinovea_annotation,
)


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
    options: ParseAnnotationOptions | None = None,
) -> ParseAnnotationResult:
    ann_file = get_with_ownership_check(db, annotation_file_id, current_user_id)
    source_value = getattr(ann_file.source, "value", str(ann_file.source))

    def _fail(exc: Exception, status_code: int = 400) -> None:
        update_annotation_file_status(db, ann_file, success=False, error_message=str(exc))
        raise HTTPException(status_code=status_code, detail=f"标注文件解析失败: {exc}")

    parsed = None
    raw = None
    raw_json = None
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
            build_metadata = parsed.model_dump()

        elif source_value == AnnotationSource.CVAT.value:
            cvat_parsed = parse_cvat_xml(ann_file.storage_path)

            session_video = ann_file.session_video
            video_file = session_video.video_file if session_video and hasattr(session_video, 'video_file') else None
            video_frame_count = int(video_file.frame_count) if video_file and hasattr(video_file, 'frame_count') and video_file.frame_count else None

            fps_source: str | None = None
            fps_verified = False
            if session_video and hasattr(session_video, 'fps') and session_video.fps:
                video_fps = float(session_video.fps)
                fps_source = "session_video"
                fps_verified = True
            elif ann_file.annotation_fps and getattr(ann_file, 'metadata', {}).get('fps_source') == 'user_provided':
                video_fps = float(ann_file.annotation_fps)
                fps_source = "annotation_file"
                fps_verified = True
            elif ann_file.annotation_fps:
                video_fps = float(ann_file.annotation_fps)
                fps_source = "annotation_file_unverified"
                fps_verified = False
            else:
                video_fps = None
                fps_source = "compatibility_default"
                fps_verified = False

            json_manifest = None
            if options and options.companion_annotation_file_id:
                companion = db.get(AnnotationFile, options.companion_annotation_file_id)
                if companion is None:
                    raise CvatParseError("MISSING_COMPANION", f"companion annotation file {options.companion_annotation_file_id} not found")
                if companion.session_video_id != ann_file.session_video_id:
                    raise CvatParseError(
                        "COMPANION_MISMATCH",
                        "companion JSON does not belong to the same session_video",
                    )
                try:
                    with open(companion.storage_path, "r", encoding="utf-8") as fh:
                        manifest_data = json.load(fh)
                    images = manifest_data.get("images", [])
                    json_manifest = [
                        {
                            "annotation_frame": i,
                            "image_name": img.get("file_name", ""),
                            "source_video_frame": img.get("source_video_frame") or img.get("frame_id"),
                            "timestamp_sec": img.get("timestamp_sec"),
                        }
                        for i, img in enumerate(images)
                    ]
                except (FileNotFoundError, json.JSONDecodeError) as exc:
                    raise CvatParseError("MANIFEST_READ_ERROR", f"failed to read companion JSON: {exc}")

            required_frames = {f.annotation_frame for f in cvat_parsed.raw_keypoint_frames}
            frame_mapping = FrameMappingResolver.resolve(
                cvat_parsed.native_metadata,
                video_fps=video_fps,
                options=options,
                json_manifest=json_manifest,
                required_annotation_frames=required_frames,
            )

            normalizer = CvatAnnotationNormalizer()
            keypoint_frames = normalizer.normalize(
                cvat_parsed.raw_keypoint_frames, frame_mapping, fps_verified=fps_verified,
            )

            derived = AnnotationDerivedDataBuilder.build(keypoint_frames)
            derived_trajectories = derived.get("trajectories", [])
            derived_warnings = derived.get("warnings", [])

            all_trajectories = derived_trajectories
            all_warnings = cvat_parsed.warnings + derived_warnings

            kf_dicts = [k.model_dump() for k in keypoint_frames]
            events = []
            trajectories = all_trajectories
            manual_tags = []
            scale = None
            coordinate_system = {"origin": "top_left", "x_axis": "right", "y_axis": "down", "unit": "pixel"}
            fps = float(video_fps) if video_fps else 60.0
            frame_count = video_frame_count
            duration_sec = float(video_file.duration_sec) if video_file and hasattr(video_file, 'duration_sec') and video_file.duration_sec else None

            annotation_sequence = {
                "frame_count": cvat_parsed.native_metadata.get("meta", {}).get("size"),
                "start_frame": cvat_parsed.native_metadata.get("meta", {}).get("start_frame", 0),
                "end_frame": cvat_parsed.native_metadata.get("meta", {}).get("stop_frame"),
            }
            annotated_frame_count = len(keypoint_frames)
            analysis_ranges = []
            if options and options.analysis_ranges:
                analysis_ranges = [r.model_dump() for r in options.analysis_ranges]

            annotation_frames = [kf.annotation_frame for kf in keypoint_frames if kf.annotation_frame is not None]
            if annotation_frames:
                annotated_ranges = build_contiguous_frame_ranges(annotation_frames)
            else:
                annotated_ranges = []

            coverage = {
                "annotated_frame_count": annotated_frame_count,
                "annotated_ranges": [r.model_dump() for r in annotated_ranges] if annotated_ranges else [],
            }

            build_metadata = {
                "video": {
                    "fps": fps,
                    "fps_source": fps_source or "compatibility_default",
                    "fps_verified": fps_verified,
                    "frame_count": video_frame_count,
                    "duration_sec": duration_sec,
                },
                "annotation_sequence": annotation_sequence,
                "frame_mapping": frame_mapping.model_dump(),
                "annotation_coverage": coverage,
                "analysis_ranges": analysis_ranges,
                "contract_version": "cvat-import-contract.v1.1",
                "parser": {
                    "name": "cvat_xml",
                    "version": "1.1.0",
                    "source_format": "cvat_task_xml",
                    "source_format_version": "1.1",
                },
                "derived": {
                    "visibility_summary": derived.get("visibility_summary", {}),
                },
            }
        else:
            with open(ann_file.storage_path, "r", encoding="utf-8") as fh:
                raw_json = json.load(fh)
            fps = raw_json.get("fps", float(ann_file.annotation_fps or 60))
            events = raw_json.get("events", [])
            keypoint_frames = raw_json.get("keypoint_frames", [])
            trajectories = raw_json.get("trajectories", [])
            manual_tags = raw_json.get("manual_tags", [])
            scale = raw_json.get("scale")
            coordinate_system = raw_json.get("coordinate_system", {})
            frame_count = raw_json.get("frame_count") or raw_json.get("video", {}).get("frame_count")
            duration_sec = raw_json.get("duration_sec") or raw_json.get("video", {}).get("duration_sec")
            build_metadata = raw_json.get("metadata", {})
    except KinoveaParseError as exc:
        _fail(exc)
    except CvatParseError as exc:
        _fail(exc)
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        _fail(exc)

    # ── quality v2 ──
    session_video = ann_file.session_video
    video_fps = float(session_video.fps) if session_video and hasattr(session_video, 'fps') and session_video.fps else None
    video_width = session_video.video_file.width if session_video and hasattr(session_video, 'video_file') and session_video.video_file else None
    video_height = session_video.video_file.height if session_video and hasattr(session_video, 'video_file') and session_video.video_file else None

    profile_id = resolve_quality_profile_id(source_value)

    validator = _get_validator()
    cvat_metadata_kwargs = {}
    if source_value == AnnotationSource.CVAT.value:
        cvat_metadata_kwargs = {
            "frame_mapping": build_metadata.get("frame_mapping"),
            "annotation_sequence": {
                "frame_count": build_metadata.get("annotation_sequence", {}).get("frame_count"),
                "annotated_frame_count": build_metadata.get("annotation_coverage", {}).get("annotated_frame_count"),
            },
            "analysis_ranges": build_metadata.get("analysis_ranges"),
            "annotated_ranges": build_metadata.get("annotation_coverage", {}).get("annotated_ranges"),
            "video_metadata": build_metadata.get("video"),
        }
    quality_report = validator.validate(
        events=events,
        keypoint_frames=keypoint_frames,
        scale=scale,
        fps=fps,
        frame_count=frame_count,
        reference_lines=raw_json.get("reference_lines") if raw_json else None,
        swim_direction=raw_json.get("swim_direction") if raw_json else None,
        video_fps=video_fps,
        video_width=video_width,
        video_height=video_height,
        view_type=str(session_video.view_type.value) if session_video and hasattr(session_video, 'view_type') else None,
        profile_id=profile_id,
        **cvat_metadata_kwargs,
    )
    quality = quality_report.model_dump(mode="json")

    # ── upsert ──
    metadata = build_metadata if build_metadata else {}
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
        existing.reference_lines = raw_json.get("reference_lines") if raw_json else None
        existing.distance_markers = raw_json.get("distance_markers") if raw_json else None
        existing.swim_direction = raw_json.get("swim_direction") if raw_json else None
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

    summary = ParseSummary(
        events_count=len(events),
        keypoint_frames_count=len(keypoint_frames),
        trajectories_count=len(trajectories),
        manual_tags_count=len(manual_tags),
    )
    warnings = all_warnings if source_value == AnnotationSource.CVAT.value else (
        parsed.warnings if parsed is not None else []
    )
    return ParseAnnotationResult(annotation=ann, summary=summary, warnings=warnings)
