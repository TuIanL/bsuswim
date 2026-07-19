from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class AnnotationSource(str, PyEnum):
    KINOVEA = "kinovea"
    DARTFISH = "dartfish"
    MANUAL_JSON = "manual_json"
    AI_POSE = "ai_pose"
    CVAT = "cvat"
    UNKNOWN = "unknown"


class AnnotationFileStatus(str, PyEnum):
    UPLOADED = "uploaded"
    PARSED = "parsed"
    PARSE_FAILED = "parse_failed"
    ARCHIVED = "archived"


class AnnotationFile(Base):
    __tablename__ = "annotation_files"
    __table_args__ = (
        UniqueConstraint("session_video_id", "source", "version", name="uq_annotation_file_session_video_source_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    session_video_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("session_videos.id", ondelete="CASCADE"), nullable=False, index=True
    )

    source: Mapped[AnnotationSource] = mapped_column(
        SQLEnum(
            AnnotationSource,
            values_callable=lambda enum: [e.value for e in enum],
        ),
        default=AnnotationSource.KINOVEA,
        nullable=False,
        index=True,
    )

    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_type: Mapped[str | None] = mapped_column(String(50))

    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))

    annotation_fps: Mapped[float | None] = mapped_column(Numeric(8, 3))
    frame_count: Mapped[int | None] = mapped_column(Integer)
    duration_sec: Mapped[float | None] = mapped_column(Numeric(10, 3))

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    status: Mapped[AnnotationFileStatus] = mapped_column(
        SQLEnum(
            AnnotationFileStatus,
            values_callable=lambda enum: [e.value for e in enum],
        ),
        default=AnnotationFileStatus.UPLOADED,
        nullable=False,
        index=True,
    )
    parse_error: Mapped[str | None] = mapped_column(Text)

    uploaded_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"))
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())

    annotation_metadata: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, server_default=text("'{}'::jsonb"))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    session_video = relationship("SessionVideo", back_populates="annotations")
    normalized_annotation = relationship("NormalizedAnnotation", back_populates="annotation_file", uselist=False)
