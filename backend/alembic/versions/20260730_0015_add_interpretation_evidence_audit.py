"""add multimodal interpretation audit fields

Revision ID: 20260730_0015
Revises: 20260730_0014
Create Date: 2026-07-30
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260730_0015"
down_revision: Union[str, None] = "20260730_0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "report_interpretations",
        sa.Column("execution_mode", sa.String(length=16), nullable=False, server_default="text"),
    )
    op.add_column(
        "report_interpretations",
        sa.Column("evidence_manifest", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column(
        "report_interpretations",
        sa.Column("evidence_exclusions", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )


def downgrade() -> None:
    op.drop_column("report_interpretations", "evidence_exclusions")
    op.drop_column("report_interpretations", "evidence_manifest")
    op.drop_column("report_interpretations", "execution_mode")
