from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session, joinedload

from app.models.annotation import AnnotationFile, AnnotationSource
from app.models.video import SessionVideo
from app.models.training_session import TrainingSession


def get_max_version(db: Session, session_video_id: int, source: AnnotationSource) -> int:
    """查询当前 session_video_id + source 下的最大版本号。"""
    result = db.scalar(
        select(func.max(AnnotationFile.version)).where(
            AnnotationFile.session_video_id == session_video_id,
            AnnotationFile.source == source,
        )
    )
    return result or 0


def list_by_session_video(db: Session, session_video_id: int) -> list[AnnotationFile]:
    """查询某个 session_video 下的全部标注文件，按版本号降序。"""
    return list(
        db.scalars(
            select(AnnotationFile)
            .where(AnnotationFile.session_video_id == session_video_id)
            .order_by(AnnotationFile.version.desc())
        ).all()
    )


def get_with_ownership_check(
    db: Session, annotation_file_id: int, current_user_id: int
) -> AnnotationFile:
    """获取标注文件并校验权限：annotation → session_video → training_session → owner。"""
    annotation = db.scalar(
        select(AnnotationFile)
        .options(
            joinedload(AnnotationFile.session_video)
            .joinedload(SessionVideo.session)
        )
        .where(AnnotationFile.id == annotation_file_id)
    )
    if not annotation:
        raise HTTPException(status_code=404, detail="标注文件不存在")

    session = annotation.session_video.session
    if session.coach_id != current_user_id:
        raise HTTPException(status_code=404, detail="标注文件不存在")

    return annotation
