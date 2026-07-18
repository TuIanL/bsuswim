"""二维运动学复核发现持久化模型（Change 5）。

与 ``annotation_metrics`` 和 ``analysis_results`` 解耦：本表只存基于
``AnnotationMetric(swim-side-kinematics.v1)`` 生成的待复核发现集合，
不写入确定性诊断，也不提前接入报告管线。
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class KinematicReviewFindingSet(Base):
    __tablename__ = "kinematic_review_finding_sets"
    __table_args__ = (
        UniqueConstraint(
            "annotation_metric_id",
            "generation_signature",
            name="uq_review_finding_set_metric_signature",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    annotation_metric_id: Mapped[int] = mapped_column(
        ForeignKey("annotation_metrics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    normalized_annotation_id: Mapped[int | None] = mapped_column(
        ForeignKey("normalized_annotations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    session_video_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    schema_version: Mapped[str] = mapped_column(String(50), nullable=False, default="swim-2d-review-findings.v1")
    rule_set: Mapped[str] = mapped_column(String(100), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    engine_version: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    threshold_basis: Mapped[str] = mapped_column(String(100), nullable=False, default="project_heuristic_v1")

    source_annotation_revision: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    source_metric_schema_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_metric_calculator: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_metric_calculator_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_metric_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    generation_signature: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ready")

    findings: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    summary: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    skipped_rules: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    warnings: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
