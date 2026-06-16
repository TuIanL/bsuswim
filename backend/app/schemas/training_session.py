from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import StrokeType, TrainingSessionStatus


class TrainingSessionCreate(BaseModel):
    athlete_id: int
    title: str = Field(min_length=1, max_length=120)
    session_date: date | None = None
    venue: str | None = Field(default=None, max_length=120)
    stroke_type: StrokeType = StrokeType.FREESTYLE
    distance_m: int | None = None
    pool_length_m: float | None = None
    notes: str | None = None


class TrainingSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    athlete_id: int
    coach_id: int | None
    title: str
    session_date: date | None
    venue: str | None
    stroke_type: StrokeType
    distance_m: int | None
    pool_length_m: float | None
    status: TrainingSessionStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime
