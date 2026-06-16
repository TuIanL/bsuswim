from datetime import date, datetime
from enum import Enum as PyEnum

from sqlalchemy import Date, DateTime, Enum as SQLEnum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class StrokeType(str, PyEnum):
    FREESTYLE = "freestyle"
    BREASTSTROKE = "breaststroke"
    BACKSTROKE = "backstroke"
    BUTTERFLY = "butterfly"
    MIXED = "mixed"


class TrainingSessionStatus(str, PyEnum):
    DRAFT = "draft"
    VIDEO_UPLOADED = "video_uploaded"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class TrainingSession(Base):
    __tablename__ = "training_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    athlete_id: Mapped[int] = mapped_column(ForeignKey("athletes.id"), nullable=False, index=True)
    coach_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    session_date: Mapped[date | None] = mapped_column(Date)
    venue: Mapped[str | None] = mapped_column(String(120))
    stroke_type: Mapped[StrokeType] = mapped_column(SQLEnum(StrokeType), default=StrokeType.FREESTYLE)
    distance_m: Mapped[int | None] = mapped_column(Integer)
    pool_length_m: Mapped[float | None] = mapped_column(Numeric(5, 2))
    status: Mapped[TrainingSessionStatus] = mapped_column(
        SQLEnum(TrainingSessionStatus),
        default=TrainingSessionStatus.DRAFT,
        nullable=False,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    athlete = relationship("Athlete", back_populates="sessions")
    coach = relationship("User", back_populates="sessions")
    videos = relationship("SessionVideo", back_populates="session", cascade="all, delete-orphan")
    analysis_tasks = relationship("AnalysisTask", back_populates="session")
