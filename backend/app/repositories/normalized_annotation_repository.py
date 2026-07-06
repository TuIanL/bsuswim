from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.annotation import AnnotationFile
from app.models.normalized_annotation import NormalizedAnnotation
from app.models.video import SessionVideo
from app.models.training_session import TrainingSession


def get_by_annotation_file(db: Session, annotation_file_id: int) -> NormalizedAnnotation | None:
    """根据 annotation_file_id 查询现有 normalized annotation（用于 upsert 判断）。"""
    return db.scalar(
        select(NormalizedAnnotation).where(NormalizedAnnotation.annotation_file_id == annotation_file_id)
    )


def list_by_session_video(db: Session, session_video_id: int) -> list[NormalizedAnnotation]:
    """查询某个 session_video 下的全部标准化标注，按创建时间降序。"""
    return list(
        db.scalars(
            select(NormalizedAnnotation)
            .where(NormalizedAnnotation.session_video_id == session_video_id)
            .order_by(NormalizedAnnotation.created_at.desc())
        ).all()
    )


def get_with_ownership_check(
    db: Session, normalized_annotation_id: int, current_user_id: int
) -> NormalizedAnnotation:
    """获取标准化标注并校验权限：normalized_annotation → session_video → training_session → coach。"""
    ann = db.scalar(
        select(NormalizedAnnotation)
        .options(
            joinedload(NormalizedAnnotation.session_video)
            .joinedload(SessionVideo.session)
        )
        .where(NormalizedAnnotation.id == normalized_annotation_id)
    )
    if not ann:
        raise HTTPException(status_code=404, detail="标准化标注不存在")

    session = ann.session_video.session
    if session.coach_id != current_user_id:
        raise HTTPException(status_code=404, detail="标准化标注不存在")

    return ann
