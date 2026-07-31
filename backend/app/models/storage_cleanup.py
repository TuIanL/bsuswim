from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class StorageCleanupFailure(Base):
    """A verified upload-root path that could not be removed after hard deletion."""

    __tablename__ = "storage_cleanup_failures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    coach_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    session_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    is_directory: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
