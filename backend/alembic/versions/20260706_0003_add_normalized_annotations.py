"""add normalized_annotations table

Revision ID: 20260706_0003
Revises: 20260706_0002
Create Date: 2026-07-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260706_0003"
down_revision: Union[str, None] = "20260706_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "normalized_annotations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_video_id", sa.Integer(), nullable=False),
        sa.Column("annotation_file_id", sa.Integer(), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("schema_version", sa.String(length=50), nullable=False, server_default=sa.text("'swim-annotation.v1'")),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("fps", sa.Numeric(precision=8, scale=3), nullable=False),
        sa.Column("frame_count", sa.Integer(), nullable=True),
        sa.Column("duration_sec", sa.Numeric(precision=10, scale=3), nullable=True),
        sa.Column("scale", postgresql.JSONB(), nullable=True),
        sa.Column("coordinate_system", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("events", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("keypoint_frames", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("trajectories", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("manual_tags", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("quality", postgresql.JSONB(), server_default=sa.text("'{\"level\": \"error\"}'::jsonb"), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["session_video_id"], ["session_videos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["annotation_file_id"], ["annotation_files.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("annotation_file_id", name="uq_normalized_annotation_file"),
    )
    op.create_index(op.f("ix_normalized_annotations_id"), "normalized_annotations", ["id"], unique=False)
    op.create_index("ix_normalized_annotations_session_video", "normalized_annotations", ["session_video_id"], unique=False)
    op.create_index("ix_normalized_annotations_annotation_file", "normalized_annotations", ["annotation_file_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_normalized_annotations_annotation_file", table_name="normalized_annotations")
    op.drop_index("ix_normalized_annotations_session_video", table_name="normalized_annotations")
    op.drop_index(op.f("ix_normalized_annotations_id"), table_name="normalized_annotations")
    op.drop_table("normalized_annotations")
