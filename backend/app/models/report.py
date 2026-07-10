from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ReportMetadata(Base):
    __tablename__ = "report_metadata"
    __table_args__ = (UniqueConstraint("session_id", name="uq_report_session"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("training_sessions.id"), nullable=False, index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("analysis_tasks.id"), unique=True, nullable=False)
    source: Mapped[str] = mapped_column(String(80), default="model_service", nullable=False)
    report_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    task = relationship("AnalysisTask", back_populates="report")

    pdf_path: Mapped[str | None] = mapped_column(String, nullable=True)
    pdf_status: Mapped[str] = mapped_column(String(50), default="not_exported")
    pdf_exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pdf_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_version: Mapped[int] = mapped_column(Integer, default=0)
