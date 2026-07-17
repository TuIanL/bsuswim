from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import (
    AnnotationFile,
    AnnotationFileStatus,
    AnnotationSource,
    NormalizedAnnotation,
    SessionVideo,
    TrainingSession,
    User,
    ViewType,
)
from app.repositories.annotation_repository import (
    get_with_ownership_check,
    list_by_session_video,
)
from app.schemas.annotation import (
    AnnotationFileArchiveResponse,
    AnnotationFileDetail,
    AnnotationFileListItem,
    AnnotationIngestResponse,
)
from app.schemas.normalized_annotation import ParseAnnotationOptions
from app.services.annotation_file_service import (
    create_annotation,
    detect_file_type,
    validate_annotation_file,
)
from app.services.annotation_ingestion_service import (
    AnnotationIngestionError,
    AnnotationIngestionResult,
    ingest_annotation,
)
from app.services.annotation_quality.readiness import derive_analysis_readiness

router = APIRouter()


def _get_owned_session(db: Session, session_id: int, current_user: User) -> TrainingSession:
    """校验 session 存在且属于当前用户。"""
    session = db.get(TrainingSession, session_id)
    if not session or session.coach_id != current_user.id:
        raise HTTPException(status_code=404, detail="训练记录不存在")
    return session


def _find_session_video(db: Session, session_id: int, video_file_id: int) -> SessionVideo:
    """查找 session_video 记录，不存在则抛出 404。"""
    link = db.scalar(
        select(SessionVideo).where(
            SessionVideo.session_id == session_id,
            SessionVideo.video_file_id == video_file_id,
        )
    )
    if not link:
        raise HTTPException(status_code=404, detail="该视频未绑定到当前训练记录")
    return link


@router.post(
    "/sessions/{session_id}/videos/{video_id}/annotations",
    status_code=status.HTTP_201_CREATED,
)
async def upload_annotation(
    session_id: int,
    video_id: int,
    file: UploadFile = File(...),
    source: str = Form(default="kinovea"),
    annotation_fps: float | None = Form(default=None),
    metadata: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传标注文件到指定训练记录下的指定视频。"""
    import json

    _get_owned_session(db, session_id, current_user)
    link = _find_session_video(db, session_id, video_id)

    # 校验 source 枚举
    try:
        source_enum = AnnotationSource(source)
    except ValueError:
        valid_sources = [s.value for s in AnnotationSource]
        raise HTTPException(
            status_code=400,
            detail=f"不支持的标注来源，仅支持: {', '.join(valid_sources)}",
        )

    # 解析 metadata
    meta_dict: dict = {}
    if metadata:
        try:
            meta_dict = json.loads(metadata)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="metadata 不是合法的 JSON")

    annotation = await create_annotation(
        db,
        file=file,
        session_video_id=link.id,
        source=source_enum,
        annotation_fps=annotation_fps,
        metadata=meta_dict,
        uploaded_by=current_user.id,
    )

    return {
        "annotation_file_id": annotation.id,
        "session_video_id": annotation.session_video_id,
        "session_id": session_id,
        "video_file_id": video_id,
        "view_type": link.view_type.value,
        "source": annotation.source.value,
        "version": annotation.version,
        "status": annotation.status.value,
        "original_filename": annotation.original_filename,
        "uploaded_at": annotation.uploaded_at.isoformat() if annotation.uploaded_at else None,
    }


@router.get("/sessions/{session_id}/videos/{video_id}/annotations")
def list_annotations(
    session_id: int,
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AnnotationFileListItem]:
    """查询某个 session video 下的全部标注文件。"""
    _get_owned_session(db, session_id, current_user)
    link = _find_session_video(db, session_id, video_id)

    annotations = list_by_session_video(db, link.id)

    na_map: dict[int, NormalizedAnnotation] = {}
    if annotations:
        nas = db.scalars(
            select(NormalizedAnnotation).where(
                NormalizedAnnotation.annotation_file_id.in_([a.id for a in annotations])
            )
        ).all()
        na_map = {na.annotation_file_id: na for na in nas}

    result: list[AnnotationFileListItem] = []
    for a in annotations:
        na = na_map.get(a.id)
        qual = na.quality if na else None
        qual_status = qual.get("status") if qual else None
        meta = na.annotation_metadata or {} if na else {}
        parse_warnings = (meta.get("parse") or {}).get("warnings", []) if meta else []

        result.append(AnnotationFileListItem(
            id=a.id,
            session_video_id=a.session_video_id,
            source=a.source,
            view_type=link.view_type,
            file_type=a.file_type,
            version=a.version,
            status=a.status,
            original_filename=a.original_filename,
            annotation_fps=float(a.annotation_fps) if a.annotation_fps else None,
            uploaded_at=a.uploaded_at,
            normalized_annotation_id=na.id if na else None,
            normalized_revision=na.revision if na else None,
            quality_status=qual_status,
            analysis_readiness=derive_analysis_readiness(qual) if qual else None,
            parse_warnings=parse_warnings,
            parse_error=a.parse_error,
        ))
    return result


@router.post(
    "/sessions/{session_id}/videos/{video_id}/annotations/ingest",
    status_code=status.HTTP_201_CREATED,
)
async def ingest_annotation_endpoint(
    session_id: int,
    video_id: int,
    file: UploadFile = File(...),
    source: str = Form(default="kinovea"),
    annotation_fps: float | None = Form(default=None),
    metadata: str | None = Form(default=None),
    parse_options: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    import json

    _get_owned_session(db, session_id, current_user)
    link = _find_session_video(db, session_id, video_id)

    try:
        source_enum = AnnotationSource(source)
    except ValueError:
        valid_sources = [s.value for s in AnnotationSource]
        raise HTTPException(
            status_code=400,
            detail=f"不支持的标注来源，仅支持: {', '.join(valid_sources)}",
        )

    meta_dict: dict = {}
    if metadata:
        try:
            meta_dict = json.loads(metadata)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="metadata 不是合法的 JSON")

    parse_opts: ParseAnnotationOptions | None = None
    if parse_options:
        try:
            parse_opts = ParseAnnotationOptions.model_validate_json(parse_options)
        except Exception:
            raise HTTPException(status_code=422, detail={
                "error": {
                    "code": "ANNOTATION_INGEST_INVALID_PARSE_OPTIONS",
                    "message": "parse_options 格式无效",
                }
            })

    try:
        result = await ingest_annotation(
            db,
            session_video_id=link.id,
            file=file,
            source=source_enum,
            annotation_fps=annotation_fps,
            metadata=meta_dict,
            parse_options=parse_opts,
            current_user_id=current_user.id,
        )
    except AnnotationIngestionError as exc:
        raise HTTPException(status_code=422, detail={
            "error": {
                "code": exc.code,
                "message": str(exc),
                "annotation_file_id": exc.annotation_file_id,
                "retryable": True,
            }
        })

    if result.parse_result is None:
        raise HTTPException(status_code=422, detail={
            "error": {
                "code": "ANNOTATION_INGEST_PARSE_FAILED",
                "message": "文件已保存但解析失败",
                "annotation_file_id": result.annotation_file.id,
                "retryable": True,
            }
        })

    return result.to_response(session_id=session_id, video_file_id=video_id)


@router.get("/annotations/{annotation_file_id}")
def get_annotation_detail(
    annotation_file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnnotationFileDetail:
    """获取单个标注文件的完整详情。"""
    annotation = get_with_ownership_check(db, annotation_file_id, current_user.id)
    link = annotation.session_video

    return AnnotationFileDetail(
        id=annotation.id,
        session_video_id=annotation.session_video_id,
        session_id=link.session_id,
        video_file_id=link.video_file_id,
        view_type=link.view_type,
        source=annotation.source,
        original_filename=annotation.original_filename,
        stored_filename=annotation.stored_filename,
        storage_path=annotation.storage_path,
        file_type=annotation.file_type,
        file_size_bytes=annotation.file_size_bytes,
        checksum_sha256=annotation.checksum_sha256,
        annotation_fps=float(annotation.annotation_fps) if annotation.annotation_fps else None,
        frame_count=annotation.frame_count,
        duration_sec=float(annotation.duration_sec) if annotation.duration_sec else None,
        version=annotation.version,
        status=annotation.status,
        parse_error=annotation.parse_error,
        metadata=annotation.annotation_metadata or {},
        uploaded_by=annotation.uploaded_by,
        uploaded_at=annotation.uploaded_at,
        created_at=annotation.created_at,
        updated_at=annotation.updated_at,
    )


@router.get("/annotations/{annotation_file_id}/download")
def download_annotation(
    annotation_file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """下载原始标注文件。"""
    annotation = get_with_ownership_check(db, annotation_file_id, current_user.id)

    file_path = Path(annotation.storage_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="标注文件不存在或已被清理")

    media_type_map = {
        "csv": "text/csv",
        "json": "application/json",
        "xml": "application/xml",
        "txt": "text/plain",
        "kva": "application/octet-stream",
    }
    media_type = media_type_map.get(annotation.file_type or "", "application/octet-stream")

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=annotation.original_filename,
    )


@router.post("/annotations/{annotation_file_id}/archive")
def archive_annotation_endpoint(
    annotation_file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnnotationFileArchiveResponse:
    """归档标注文件（不物理删除）。"""
    from app.services.annotation_file_service import archive_annotation

    annotation = archive_annotation(db, annotation_file_id, current_user.id)
    return AnnotationFileArchiveResponse(
        id=annotation.id,
        status=annotation.status,
    )
