from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.models.annotation import AnnotationFileStatus, AnnotationSource
from app.repositories.normalized_annotation_repository import (
    get_with_ownership_check,
    list_by_session_video,
)
from app.schemas.normalized_annotation import (
    NormalizedAnnotationCreate,
    NormalizedAnnotationListItem,
    NormalizedAnnotationRead,
    ParseAnnotationOptions,
    ParseResponse,
)
from app.services.annotation_quality.legacy import normalize_quality_payload
from app.services.annotation_quality.profile_resolver import resolve_quality_profile_id
from app.services.annotation_quality.readiness import derive_analysis_readiness
from app.services.annotation_quality.validator import AnnotationQualityValidator
from app.services.annotation_quality.provider import YamlQualityProfileProvider
from app.services.normalized_annotation_service import (
    create_normalized_annotation,
    parse_annotation_file,
)

import os

router = APIRouter()


def _get_validator() -> AnnotationQualityValidator:
    profiles_dir = os.path.join(os.path.dirname(__file__), "..", "..", "services", "annotation_quality", "profiles")
    provider = YamlQualityProfileProvider(profiles_dir)
    return AnnotationQualityValidator(profile_provider=provider)


# ── Create from JSON ──


@router.post(
    "/session-videos/{session_video_id}/normalized-annotations",
    status_code=status.HTTP_201_CREATED,
)
def create_normalized_annotation_endpoint(
    session_video_id: int,
    data: NormalizedAnnotationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ann = create_normalized_annotation(
        db,
        session_video_id=session_video_id,
        data=data,
        created_by=current_user.id,
    )
    quality = ann.quality or {}
    return {
        "id": ann.id,
        "session_video_id": ann.session_video_id,
        "annotation_file_id": ann.annotation_file_id,
        "schema_version": ann.schema_version,
        "source": ann.source,
        "revision": ann.revision,
        "quality": quality,
        "analysis_readiness": derive_analysis_readiness(quality),
    }


# ── Get by ID ──


@router.get("/normalized-annotations/{normalized_annotation_id}")
def get_normalized_annotation(
    normalized_annotation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NormalizedAnnotationRead:
    ann = get_with_ownership_check(db, normalized_annotation_id, current_user.id)
    link = ann.session_video

    return NormalizedAnnotationRead(
        id=ann.id,
        session_video_id=ann.session_video_id,
        session_id=link.session_id,
        video_file_id=link.video_file_id,
        view_type=link.view_type,
        annotation_file_id=ann.annotation_file_id,
        revision=ann.revision,
        schema_version=ann.schema_version,
        source=ann.source,
        fps=float(ann.fps) if ann.fps else 0,
        frame_count=ann.frame_count,
        duration_sec=float(ann.duration_sec) if ann.duration_sec else None,
        scale=ann.scale,
        coordinate_system=ann.coordinate_system or {},
        events=ann.events or [],
        keypoint_frames=ann.keypoint_frames or [],
        trajectories=ann.trajectories or [],
        manual_tags=ann.manual_tags or [],
        reference_lines=ann.reference_lines,
        distance_markers=ann.distance_markers,
        swim_direction=ann.swim_direction,
        quality=ann.quality or {},
        annotation_metadata=ann.annotation_metadata or {},
        created_by=ann.created_by,
        created_at=ann.created_at,
        updated_at=ann.updated_at,
    )


# ── List by session video ──


@router.get("/session-videos/{session_video_id}/normalized-annotations")
def list_normalized_annotations(
    session_video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[NormalizedAnnotationListItem]:
    annotations = list_by_session_video(db, session_video_id)
    return [
        NormalizedAnnotationListItem(
            id=a.id,
            session_video_id=a.session_video_id,
            annotation_file_id=a.annotation_file_id,
            revision=a.revision,
            schema_version=a.schema_version,
            source=a.source,
            view_type=a.session_video.view_type if a.session_video else None,
            quality_level=a.quality.get("level") or a.quality.get("status") if a.quality else None,
            created_at=a.created_at,
        )
        for a in annotations
    ]


# ── Parse annotation file ──


@router.post(
    "/annotations/{annotation_file_id}/parse",
    status_code=status.HTTP_201_CREATED,
    response_model=ParseResponse,
)
def parse_annotation_file_endpoint(
    annotation_file_id: int,
    options: ParseAnnotationOptions | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = parse_annotation_file(db, annotation_file_id, current_user_id=current_user.id, options=options)
    ann = result.annotation
    quality = normalize_quality_payload(ann.quality or {})
    readiness = derive_analysis_readiness(ann.quality or {})
    return ParseResponse(
        normalized_annotation_id=ann.id,
        annotation_file_id=annotation_file_id,
        source=AnnotationSource(ann.source),
        status=AnnotationFileStatus.PARSED,
        schema_version=ann.schema_version,
        revision=ann.revision,
        summary=result.summary,
        quality=quality,
        analysis_readiness=readiness,
        warnings=result.warnings,
    )


# ── Re-validate ──


@router.post("/normalized-annotations/{normalized_annotation_id}/validate")
def revalidate_normalized_annotation(
    normalized_annotation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    force: bool = False,
):
    ann = get_with_ownership_check(db, normalized_annotation_id, current_user.id)
    current_quality = normalize_quality_payload(ann.quality)

    VALIDATOR_VERSION = "1.0.0"
    PROFILE_ID = resolve_quality_profile_id(ann.source)
    PROFILE_VERSION = "1.0.0"

    if not force:
        cached_revision = current_quality.source_revision
        cached_validator = current_quality.validator_version
        cached_profile_id = current_quality.profile.id if current_quality.profile else None
        cached_profile_ver = current_quality.profile.version if current_quality.profile else None

        if (cached_revision == ann.revision
                and cached_validator == VALIDATOR_VERSION
                and cached_profile_id == PROFILE_ID
                and cached_profile_ver == PROFILE_VERSION):
            return {
                "normalized_annotation_id": ann.id,
                "revision": ann.revision,
                "quality": current_quality.model_dump(mode="json"),
                "analysis_readiness": derive_analysis_readiness(ann.quality),
                "cached": True,
            }

    report = _get_validator().validate(
        events=ann.events or [],
        keypoint_frames=ann.keypoint_frames or [],
        scale=ann.scale,
        fps=float(ann.fps) if ann.fps else None,
        frame_count=ann.frame_count,
        reference_lines=ann.reference_lines,
        swim_direction=ann.swim_direction,
        source_revision=ann.revision,
        validator_version=VALIDATOR_VERSION,
    )

    ann.quality = report.model_dump(mode="json")
    db.add(ann)
    db.commit()
    db.refresh(ann)

    return {
        "normalized_annotation_id": ann.id,
        "revision": ann.revision,
        "quality": report.model_dump(mode="json"),
        "analysis_readiness": derive_analysis_readiness(ann.quality),
        "cached": False,
    }
