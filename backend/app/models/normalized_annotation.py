from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class NormalizedAnnotation(Base):
    __tablename__ = "normalized_annotations"
    __table_args__ = (
        UniqueConstraint("annotation_file_id", name="uq_normalized_annotation_file"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    session_video_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("session_videos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    annotation_file_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("annotation_files.id", ondelete="SET NULL"), nullable=True
    )

    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))

    schema_version: Mapped[str] = mapped_column(
        String(50), nullable=False, default="swim-annotation.v1", server_default=text("'swim-annotation.v1'")
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False)

    fps: Mapped[float] = mapped_column(Numeric(8, 3), nullable=False)
    frame_count: Mapped[int | None] = mapped_column(Integer)
    duration_sec: Mapped[float | None] = mapped_column(Numeric(10, 3))

    scale: Mapped[dict | None] = mapped_column(JSONB)
    coordinate_system: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))

    events: Mapped[list] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))
    keypoint_frames: Mapped[list] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))
    trajectories: Mapped[list] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))
    manual_tags: Mapped[list] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))

    # ── side-view metrics 上下文（Change #4 新增）──
    reference_lines: Mapped[dict | None] = mapped_column(JSONB)
    distance_markers: Mapped[list | None] = mapped_column(JSONB)
    swim_direction: Mapped[str | None] = mapped_column(String(20))

    quality: Mapped[dict] = mapped_column(
        JSONB, default=lambda: {"level": "error"}, server_default=text("'{\"level\": \"error\"}'::jsonb")
    )
    annotation_metadata: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, server_default=text("'{}'::jsonb")
    )

    created_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    session_video = relationship("SessionVideo", back_populates="normalized_annotations")
    annotation_file = relationship("AnnotationFile", back_populates="normalized_annotation")
