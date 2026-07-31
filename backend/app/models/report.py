from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, func
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
    interpretations = relationship(
        "ReportInterpretation",
        back_populates="report",
        cascade="all, delete-orphan",
    )

    pdf_path: Mapped[str | None] = mapped_column(String, nullable=True)
    pdf_status: Mapped[str] = mapped_column(String(50), default="not_exported")
    pdf_exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pdf_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_version: Mapped[int] = mapped_column(Integer, default=0)


class ReportInterpretation(Base):
    __tablename__ = "report_interpretations"
    __table_args__ = (
        UniqueConstraint(
            "report_metadata_id",
            "generation_signature",
            "attempt",
            name="uq_report_interpretation_attempt",
        ),
        Index(
            "ix_report_interpretation_current",
            "report_metadata_id",
            "base_report_generation_signature",
            "status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_metadata_id: Mapped[int] = mapped_column(
        ForeignKey("report_metadata.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requested_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    base_report_generation_signature: Mapped[str] = mapped_column(String(128), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    generation_signature: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    force_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    model_parameters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    output_schema_version: Mapped[str] = mapped_column(String(80), nullable=False)
    knowledge_base_version: Mapped[str] = mapped_column(String(64), nullable=False)
    knowledge_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    execution_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="text")
    evidence_manifest: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    evidence_exclusions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    content: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    validation_result: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    usage: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retryable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    report = relationship("ReportMetadata", back_populates="interpretations")
