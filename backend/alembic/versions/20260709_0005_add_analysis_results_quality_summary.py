# ============================================================
# 迁移脚本 0005：为 analysis_results 增加 quality_summary 列
# ============================================================
# 作用：Change #5 的接线桥在写回诊断结果时，需要把 adapter 产出的
#       quality_summary（标注质量概览）持久化到 analysis_results，供
#       Change #6 report_builder 与前端展示使用。
#
# 说明：analysis_results.diagnostics 列已由迁移 0001 创建（JSON），
#       本迁移只新增 quality_summary，不重复加列。
#
# 这是迁移链的第五环：down_revision 指向 0004。
# ============================================================

"""add analysis_results.quality_summary

Revision ID: 20260709_0005
Revises: 20260709_0004
Create Date: 2026-07-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260709_0005"
down_revision: Union[str, None] = "20260709_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "analysis_results",
        sa.Column("quality_summary", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
    )


def downgrade() -> None:
    op.drop_column("analysis_results", "quality_summary")
