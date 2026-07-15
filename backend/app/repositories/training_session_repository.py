from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.training_session import TrainingSession


def require_owned_session(
    db: Session,
    *,
    session_id: int,
    user_id: int,
) -> TrainingSession:
    session = db.get(TrainingSession, session_id)
    if not session or session.coach_id != user_id:
        raise HTTPException(status_code=404, detail="训练记录不存在")
    return session
