from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ViewType(str, PyEnum):
    SIDE = "side"
    FRONT = "front"
    TOP = "top"
    UNDERWATER = "underwater"
    OTHER = "other"


class VideoFile(Base):
    __tablename__ = "video_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(120))
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session_links = relationship("SessionVideo", back_populates="video_file")


class SessionVideo(Base):
    __tablename__ = "session_videos"
    __table_args__ = (UniqueConstraint("session_id", "video_file_id", name="uq_session_video_file"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("training_sessions.id"), nullable=False, index=True)
    video_file_id: Mapped[int] = mapped_column(ForeignKey("video_files.id"), nullable=False, index=True)
    view_type: Mapped[ViewType] = mapped_column(SQLEnum(ViewType), default=ViewType.SIDE, nullable=False)
    fps: Mapped[float | None] = mapped_column(Numeric(6, 2))
    resolution: Mapped[str | None] = mapped_column(String(40))
    sync_offset_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session = relationship("TrainingSession", back_populates="videos")
    video_file = relationship("VideoFile", back_populates="session_links")
