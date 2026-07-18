"""Kinematic artifact persistence models (Change 4)."""

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.services.kinematic_artifacts.constants import (
    SCHEMA_VERSION,
    GENERATOR_NAME,
    GENERATOR_VERSION,
    STYLE_PROFILE,
)


class KinematicArtifactSet(Base):
    __tablename__ = "kinematic_artifact_sets"
    __table_args__ = (
        UniqueConstraint(
            "annotation_metric_id",
            "generation_signature",
            name="uq_artifact_set_metric_signature",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    annotation_metric_id: Mapped[int] = mapped_column(
        ForeignKey("annotation_metrics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    normalized_annotation_id: Mapped[int] = mapped_column(
        ForeignKey("normalized_annotations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_video_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    schema_version: Mapped[str] = mapped_column(String(50), nullable=False, default=SCHEMA_VERSION)

    generator: Mapped[str] = mapped_column(String(50), nullable=False, default=GENERATOR_NAME)
    generator_version: Mapped[str] = mapped_column(String(50), nullable=False, default=GENERATOR_VERSION)
    style_profile: Mapped[str] = mapped_column(String(50), nullable=False, default=STYLE_PROFILE)

    source_annotation_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    source_metric_schema_version: Mapped[str] = mapped_column(String(50), nullable=False)
    source_metric_calculator: Mapped[str] = mapped_column(String(100), nullable=False)
    source_metric_calculator_version: Mapped[str] = mapped_column(String(50), nullable=False)
    source_metric_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    generation_signature: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="generating")

    manifest: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    manifest_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    warnings: Mapped[list] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))

    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    artifacts: Mapped[list["KinematicArtifact"]] = relationship(
        "KinematicArtifact",
        back_populates="artifact_set",
        cascade="all, delete-orphan",
        order_by="KinematicArtifact.id",
    )


class KinematicArtifact(Base):
    __tablename__ = "kinematic_artifacts"
    __table_args__ = (
        UniqueConstraint(
            "artifact_set_id", "artifact_key", name="uq_artifact_set_key"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    artifact_set_id: Mapped[int] = mapped_column(
        ForeignKey("kinematic_artifact_sets.id", ondelete="CASCADE"), nullable=False, index=True
    )

    artifact_key: Mapped[str] = mapped_column(String(120), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(40), nullable=False)
    module_key: Mapped[str] = mapped_column(String(40), nullable=False)
    metric_keys: Mapped[list] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ready")

    annotation_frame: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_video_frame: Mapped[int | None] = mapped_column(Integer, nullable=True)

    annotation_frame_range: Mapped[dict | None] = mapped_column(JSONB)
    source_video_frame_range: Mapped[dict | None] = mapped_column(JSONB)

    storage_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)

    skip_reason: Mapped[str | None] = mapped_column(String(60), nullable=True)
    artifact_metadata: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, server_default=text("'{}'::jsonb"))

    artifact_set: Mapped["KinematicArtifactSet"] = relationship(
        "KinematicArtifactSet", back_populates="artifacts"
    )
