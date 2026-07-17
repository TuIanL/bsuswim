# ============================================================
# 迁移脚本 0008：为 annotation_metrics 增加 source_revision 列
# ============================================================
# 作用：
#   支撑 side_2d_kinematics calculator 的「修订三态」检测：
#     - source_revision == NULL        → revision_status = unknown
#     - source_revision == ann.revision → revision_status = current
#     - source_revision != ann.revision → revision_status = stale
#
# 不改动任何其他表结构。旧记录 source_revision=NULL 仍可读（unknown 而非 stale）。
# ============================================================

"""add source_revision to annotation_metrics

Revision ID: 20260717_0008
Revises: 20260714_0007
Create Date: 2026-07-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260717_0008"
down_revision: Union[str, None] = "20260714_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "annotation_metrics",
        sa.Column("source_revision", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_annotation_metrics_source_revision",
        "annotation_metrics",
        ["source_revision"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_annotation_metrics_source_revision", table_name="annotation_metrics")
    op.drop_column("annotation_metrics", "source_revision")
