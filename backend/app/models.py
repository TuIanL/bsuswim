from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class AnalysisTaskStatus(str, PyEnum):
    UPLOADED = "uploaded"
    QUEUED = "queued"
    PROCESSING = "processing"
    RESULT_SAVING = "result_saving"
    COMPLETED = "completed"
    FAILED = "failed"


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

    tasks: Mapped[list["AnalysisTask"]] = relationship(back_populates="video")


class AnalysisTask(Base):
    __tablename__ = "analysis_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("video_files.id"), nullable=False, index=True)
    status: Mapped[AnalysisTaskStatus] = mapped_column(
        SQLEnum(AnalysisTaskStatus), default=AnalysisTaskStatus.QUEUED, nullable=False, index=True
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stage: Mapped[str] = mapped_column(String(80), default="queued", nullable=False)
    session_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    video: Mapped[VideoFile] = relationship(back_populates="tasks")
    result: Mapped["AnalysisResult | None"] = relationship(back_populates="task", uselist=False)
    report: Mapped["ReportMetadata | None"] = relationship(back_populates="task", uselist=False)


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("analysis_tasks.id"), unique=True, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(40), nullable=False)
    detections: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    keypoint_frames: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    phases: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    metrics: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    diagnostics: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    raw_result: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    task: Mapped[AnalysisTask] = relationship(back_populates="result")


class ReportMetadata(Base):
    __tablename__ = "report_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("analysis_tasks.id"), unique=True, nullable=False)
    source: Mapped[str] = mapped_column(String(80), default="model_service", nullable=False)
    report_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    task: Mapped[AnalysisTask] = relationship(back_populates="report")
