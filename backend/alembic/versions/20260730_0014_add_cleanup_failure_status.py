"""add cleanup failure status

Revision ID: 20260730_0014
Revises: 20260730_0013
Create Date: 2026-07-30
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260730_0014"
down_revision: Union[str, None] = "20260730_0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "storage_cleanup_failures",
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
    )


def downgrade() -> None:
    op.drop_column("storage_cleanup_failures", "status")
