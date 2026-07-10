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
    AnnotationQuality,
    NormalizedAnnotationCreate,
    NormalizedAnnotationListItem,
    NormalizedAnnotationRead,
    ParseResponse,
)
from app.services.normalized_annotation_service import (
    create_normalized_annotation,
    parse_annotation_file,
)

router = APIRouter()


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
    """从 JSON 数据创建标准化标注记录。"""
    ann = create_normalized_annotation(
        db,
        session_video_id=session_video_id,
        data=data,
        created_by=current_user.id,
    )
    return {
        "id": ann.id,
        "session_video_id": ann.session_video_id,
        "annotation_file_id": ann.annotation_file_id,
        "schema_version": ann.schema_version,
        "source": ann.source,
        "revision": ann.revision,
        "quality": ann.quality,
    }


# ── Get by ID ──


@router.get("/normalized-annotations/{normalized_annotation_id}")
def get_normalized_annotation(
    normalized_annotation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NormalizedAnnotationRead:
    """获取单条标准化标注的完整详情。"""
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
    """查询某个 session video 下的全部标准化标注。"""
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
            quality_level=a.quality.get("level") if a.quality else None,
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """解析 annotation_file 生成标准化标注（Kinovea JSON/CSV 或 manual_json）。"""
    result = parse_annotation_file(db, annotation_file_id, current_user_id=current_user.id)
    ann = result.annotation
    quality = AnnotationQuality(**ann.quality) if ann.quality else AnnotationQuality(level="error")
    return ParseResponse(
        normalized_annotation_id=ann.id,
        annotation_file_id=annotation_file_id,
        source=AnnotationSource(ann.source),
        status=AnnotationFileStatus.PARSED,
        schema_version=ann.schema_version,
        revision=ann.revision,
        summary=result.summary,
        quality=quality,
        warnings=result.warnings,
    )
