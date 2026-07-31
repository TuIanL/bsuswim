from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.api.routes.videos import _read_video
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import Athlete, SessionVideo, StorageCleanupFailure, TrainingSession, TrainingSessionStatus, User, VideoFile
from app.schemas import (
    SessionVideoCreate,
    SessionVideoRead,
    StorageCleanupFailureRead,
    StorageCleanupRetryRead,
    TrainingSessionCreate,
    TrainingSessionRead,
)
from app.services.history_deletion_service import (
    ActiveAnalysisTaskError,
    HistoryNotFoundError,
    StorageCleanupError,
    UnsafeStoragePathError,
    delete_training_history,
    retry_storage_cleanup,
)

router = APIRouter()


@router.post("", response_model=TrainingSessionRead, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: TrainingSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TrainingSessionRead:
    athlete = db.get(Athlete, payload.athlete_id)
    if not athlete or athlete.coach_id != current_user.id:
        raise HTTPException(status_code=404, detail="运动员不存在")

    session = TrainingSession(**payload.model_dump(), coach_id=current_user.id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("", response_model=list[TrainingSessionRead])
def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TrainingSessionRead]:
    query = (
        select(TrainingSession)
        .where(TrainingSession.coach_id == current_user.id)
        .order_by(TrainingSession.created_at.desc())
    )
    return list(db.scalars(query).all())


@router.get("/cleanup-failures", response_model=list[StorageCleanupFailureRead])
def list_cleanup_failures(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[StorageCleanupFailure]:
    return list(
        db.scalars(
            select(StorageCleanupFailure)
            .where(StorageCleanupFailure.coach_id == current_user.id, StorageCleanupFailure.resolved_at.is_(None))
            .order_by(StorageCleanupFailure.created_at.desc())
        ).all()
    )


@router.post("/cleanup-failures/{failure_id}/retry", response_model=StorageCleanupRetryRead)
def retry_cleanup_failure(
    failure_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StorageCleanupRetryRead:
    try:
        resolved = retry_storage_cleanup(db, failure_id, current_user.id)
    except HistoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail="清理失败记录不存在") from exc
    return StorageCleanupRetryRead(id=failure_id, resolved=resolved)


@router.get("/{session_id}", response_model=TrainingSessionRead)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TrainingSessionRead:
    session = _get_owned_session(db, session_id, current_user)
    return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    try:
        delete_training_history(db, session_id, current_user.id)
    except HistoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail="训练记录不存在") from exc
    except ActiveAnalysisTaskError as exc:
        raise HTTPException(status_code=409, detail="分析任务仍在进行，暂时不能删除") from exc
    except UnsafeStoragePathError as exc:
        raise HTTPException(status_code=400, detail="关联文件路径无效，未执行删除") from exc
    except StorageCleanupError as exc:
        raise HTTPException(
            status_code=500,
            detail={"message": "数据库记录已删除，但部分文件清理失败", "cleanup_failure_ids": exc.failure_ids},
        ) from exc


@router.post("/{session_id}/videos", response_model=SessionVideoRead, status_code=status.HTTP_201_CREATED)
def bind_session_video(
    session_id: int,
    payload: SessionVideoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionVideoRead:
    session = _get_owned_session(db, session_id, current_user)
    video = db.get(VideoFile, payload.video_file_id)
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")

    link = SessionVideo(session_id=session.id, **payload.model_dump())
    session.status = TrainingSessionStatus.VIDEO_UPLOADED
    db.add(link)
    db.add(session)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="该视频已绑定到此训练记录") from exc
    db.refresh(link)
    link.video_file = video
    return _read_session_video(link)


@router.get("/{session_id}/videos", response_model=list[SessionVideoRead])
def list_session_videos(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SessionVideoRead]:
    _get_owned_session(db, session_id, current_user)
    links = db.scalars(
        select(SessionVideo)
        .where(SessionVideo.session_id == session_id)
        .options(joinedload(SessionVideo.video_file))
        .order_by(SessionVideo.created_at.asc())
    ).all()
    return [_read_session_video(link) for link in links]


def _get_owned_session(db: Session, session_id: int, current_user: User) -> TrainingSession:
    session = db.get(TrainingSession, session_id)
    if not session or session.coach_id != current_user.id:
        raise HTTPException(status_code=404, detail="训练记录不存在")
    return session


def _read_session_video(link: SessionVideo) -> SessionVideoRead:
    return SessionVideoRead.model_validate(
        {
            **link.__dict__,
            "video": _read_video(link.video_file),
        }
    )
