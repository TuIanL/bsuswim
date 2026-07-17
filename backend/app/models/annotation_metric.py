from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AnnotationMetric(Base):
    """side-view metrics 的持久化表（Change #4）。

    与 ``analysis_results`` 解耦：本表只存基于 ``NormalizedAnnotation`` 的确定性
    事实指标计算产物，不接入外部模型服务管线。
    """

    __tablename__ = "annotation_metrics"
    __table_args__ = (
        UniqueConstraint(
            "normalized_annotation_id",
            "calculator",
            "calculator_version",
            name="uq_annotation_metrics_calc",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    normalized_annotation_id: Mapped[int] = mapped_column(
        ForeignKey("normalized_annotations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_video_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    schema_version: Mapped[str] = mapped_column(String(50), nullable=False, default="swim-side-metrics.v1")
    camera_view: Mapped[str] = mapped_column(String(50), nullable=False, default="side")

    metrics: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    quality: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    calculator: Mapped[str] = mapped_column(String(100), nullable=False, default="side_view_metrics")
    calculator_version: Mapped[str] = mapped_column(String(50), nullable=False, default="0.1.0")

    source_revision: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
