"""add storage cleanup failures

Revision ID: 20260730_0013
Revises: 20260730_0012
Create Date: 2026-07-30
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260730_0013"
down_revision: Union[str, None] = "20260730_0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "storage_cleanup_failures",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("coach_id", sa.Integer(), nullable=True),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
        sa.Column("is_directory", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["coach_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_storage_cleanup_failures_coach_id", "storage_cleanup_failures", ["coach_id"])
    op.create_index("ix_storage_cleanup_failures_session_id", "storage_cleanup_failures", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_storage_cleanup_failures_session_id", table_name="storage_cleanup_failures")
    op.drop_index("ix_storage_cleanup_failures_coach_id", table_name="storage_cleanup_failures")
    op.drop_table("storage_cleanup_failures")
