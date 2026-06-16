from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class AthleteCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    gender: str | None = Field(default=None, max_length=20)
    birth_date: date | None = None
    height_cm: float | None = None
    weight_kg: float | None = None
    stroke_specialty: str | None = Field(default=None, max_length=40)
    level: str | None = Field(default=None, max_length=40)
    team_id: int | None = None
    notes: str | None = None


class AthleteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    gender: str | None
    birth_date: date | None
    height_cm: float | None
    weight_kg: float | None
    stroke_specialty: str | None
    level: str | None
    coach_id: int | None
    team_id: int | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
