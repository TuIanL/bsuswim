from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import Athlete, TrainingSession, User
from app.schemas import AthleteCreate, AthleteRead, TrainingSessionRead

router = APIRouter()


@router.post("", response_model=AthleteRead, status_code=status.HTTP_201_CREATED)
def create_athlete(
    payload: AthleteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AthleteRead:
    athlete = Athlete(**payload.model_dump(), coach_id=current_user.id)
    db.add(athlete)
    db.commit()
    db.refresh(athlete)
    return athlete


@router.get("", response_model=list[AthleteRead])
def list_athletes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AthleteRead]:
    query = select(Athlete).where(Athlete.coach_id == current_user.id).order_by(Athlete.created_at.desc())
    return list(db.scalars(query).all())


@router.get("/{athlete_id}", response_model=AthleteRead)
def get_athlete(
    athlete_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AthleteRead:
    athlete = db.get(Athlete, athlete_id)
    if not athlete or athlete.coach_id != current_user.id:
        raise HTTPException(status_code=404, detail="运动员不存在")
    return athlete


@router.get("/{athlete_id}/sessions", response_model=list[TrainingSessionRead])
def list_athlete_sessions(
    athlete_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TrainingSessionRead]:
    athlete = db.get(Athlete, athlete_id)
    if not athlete or athlete.coach_id != current_user.id:
        raise HTTPException(status_code=404, detail="运动员不存在")

    query = (
        select(TrainingSession)
        .where(TrainingSession.athlete_id == athlete_id, TrainingSession.coach_id == current_user.id)
        .order_by(TrainingSession.created_at.desc())
    )
    return list(db.scalars(query).all())
