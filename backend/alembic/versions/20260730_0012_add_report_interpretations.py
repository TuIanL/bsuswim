"""add report interpretations

Revision ID: 20260730_0012
Revises: 20260718_0011
Create Date: 2026-07-30
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260730_0012"
down_revision: Union[str, None] = "20260718_0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "report_interpretations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("report_metadata_id", sa.Integer(), nullable=False),
        sa.Column("requested_by_user_id", sa.Integer(), nullable=True),
        sa.Column("base_report_generation_signature", sa.String(128), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("generation_signature", sa.String(64), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("force_requested", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("provider", sa.String(80), nullable=False),
        sa.Column("model", sa.String(120), nullable=False),
        sa.Column("model_parameters", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("prompt_version", sa.String(50), nullable=False),
        sa.Column("output_schema_version", sa.String(80), nullable=False),
        sa.Column("knowledge_base_version", sa.String(64), nullable=False),
        sa.Column("knowledge_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("content", sa.JSON(), nullable=True),
        sa.Column("validation_result", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("usage", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retryable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["report_metadata_id"], ["report_metadata.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint(
            "report_metadata_id", "generation_signature", "attempt",
            name="uq_report_interpretation_attempt",
        ),
    )
    op.create_index("ix_report_interpretations_report_metadata_id", "report_interpretations", ["report_metadata_id"])
    op.create_index("ix_report_interpretations_requested_by_user_id", "report_interpretations", ["requested_by_user_id"])
    op.create_index("ix_report_interpretations_generation_signature", "report_interpretations", ["generation_signature"])
    op.create_index("ix_report_interpretations_status", "report_interpretations", ["status"])
    op.create_index(
        "ix_report_interpretation_current",
        "report_interpretations",
        ["report_metadata_id", "base_report_generation_signature", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_report_interpretation_current", table_name="report_interpretations")
    op.drop_index("ix_report_interpretations_status", table_name="report_interpretations")
    op.drop_index("ix_report_interpretations_generation_signature", table_name="report_interpretations")
    op.drop_index("ix_report_interpretations_report_metadata_id", table_name="report_interpretations")
    op.drop_index("ix_report_interpretations_requested_by_user_id", table_name="report_interpretations")
    op.drop_table("report_interpretations")
