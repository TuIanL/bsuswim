# ============================================================
# 迁移脚本 0004：新增侧面指标所需的标注字段 + annotation_metrics 表
# ============================================================
# 作用：
#   1) 为 normalized_annotations 增加 reference_lines / distance_markers / swim_direction
#      三个 JSONB/字符串列，支撑富指标（髋深、速度、划幅、相位）计算。
#   2) 新建 annotation_metrics 表，独立持久化 side-view metrics 计算产物，
#      不复用 analysis_results，不接入模型服务管线。
#
# 这是迁移链的第四环：down_revision 指向 0003。
# ============================================================

"""add annotation_metrics table and side-view metric fields

Revision ID: 20260709_0004
Revises: 20260706_0003
Create Date: 2026-07-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260709_0004"
down_revision: Union[str, None] = "20260706_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ============================================================
# 升级
# ============================================================
def upgrade() -> None:
    # ── 1) normalized_annotations 新增三列 ──
    op.add_column(
        "normalized_annotations",
        sa.Column("reference_lines", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "normalized_annotations",
        sa.Column("distance_markers", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "normalized_annotations",
        sa.Column("swim_direction", sa.String(length=20), nullable=True),
    )

    # ── 2) 新建 annotation_metrics 表 ──
    op.create_table(
        "annotation_metrics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("normalized_annotation_id", sa.Integer(), nullable=False),
        sa.Column("session_video_id", sa.Integer(), nullable=True),
        sa.Column("schema_version", sa.String(length=50), nullable=False, server_default=sa.text("'swim-side-metrics.v1'")),
        sa.Column("camera_view", sa.String(length=50), nullable=False, server_default=sa.text("'side'")),
        sa.Column("metrics", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("quality", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("calculator", sa.String(length=100), nullable=False, server_default=sa.text("'side_view_metrics'")),
        sa.Column("calculator_version", sa.String(length=50), nullable=False, server_default=sa.text("'0.1.0'")),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["normalized_annotation_id"], ["normalized_annotations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "normalized_annotation_id", "calculator", "calculator_version",
            name="uq_annotation_metrics_calc",
        ),
    )
    op.create_index(op.f("ix_annotation_metrics_id"), "annotation_metrics", ["id"], unique=False)
    op.create_index(
        "ix_annotation_metrics_normalized_annotation",
        "annotation_metrics",
        ["normalized_annotation_id"],
        unique=False,
    )
    op.create_index(
        "ix_annotation_metrics_session_video", "annotation_metrics", ["session_video_id"], unique=False
    )


# ============================================================
# 降级
# ============================================================
def downgrade() -> None:
    op.drop_index("ix_annotation_metrics_session_video", table_name="annotation_metrics")
    op.drop_index("ix_annotation_metrics_normalized_annotation", table_name="annotation_metrics")
    op.drop_index(op.f("ix_annotation_metrics_id"), table_name="annotation_metrics")
    op.drop_table("annotation_metrics")

    op.drop_column("normalized_annotations", "swim_direction")
    op.drop_column("normalized_annotations", "distance_markers")
    op.drop_column("normalized_annotations", "reference_lines")
