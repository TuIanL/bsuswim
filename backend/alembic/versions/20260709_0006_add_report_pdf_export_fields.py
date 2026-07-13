"""add PDF export fields to report_metadata

Revision ID: 20260709_0006
Revises: 20260709_0005
Create Date: 2026-07-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260709_0006"
down_revision: Union[str, None] = "20260709_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "report_metadata",
        sa.Column("pdf_path", sa.String(), nullable=True),
    )
    op.add_column(
        "report_metadata",
        sa.Column("pdf_status", sa.String(length=50), nullable=False, server_default=sa.text("'not_exported'")),
    )
    op.add_column(
        "report_metadata",
        sa.Column("pdf_exported_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "report_metadata",
        sa.Column("pdf_error", sa.Text(), nullable=True),
    )
    op.add_column(
        "report_metadata",
        sa.Column("pdf_version", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )


def downgrade() -> None:
    op.drop_column("report_metadata", "pdf_version")
    op.drop_column("report_metadata", "pdf_error")
    op.drop_column("report_metadata", "pdf_exported_at")
    op.drop_column("report_metadata", "pdf_status")
    op.drop_column("report_metadata", "pdf_path")
