"""add annotation_files table

Revision ID: 20260706_0002
Revises: 20260616_0001
Create Date: 2026-07-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260706_0002"
down_revision: Union[str, None] = "20260616_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

annotation_source = postgresql.ENUM(
    "kinovea", "dartfish", "manual_json", "ai_pose", "unknown",
    name="annotationsource",
    create_type=False,
)
annotation_file_status = postgresql.ENUM(
    "uploaded", "parsed", "parse_failed", "archived",
    name="annotationfilestatus",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    annotation_source.create(bind, checkfirst=True)
    annotation_file_status.create(bind, checkfirst=True)

    op.create_table(
        "annotation_files",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_video_id", sa.Integer(), nullable=False),
        sa.Column("source", annotation_source, nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("file_type", sa.String(length=50), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("annotation_fps", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column("frame_count", sa.Integer(), nullable=True),
        sa.Column("duration_sec", sa.Numeric(precision=10, scale=3), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", annotation_file_status, nullable=False),
        sa.Column("parse_error", sa.Text(), nullable=True),
        sa.Column("uploaded_by", sa.Integer(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["session_video_id"], ["session_videos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_video_id", "source", "version", name="uq_annotation_file_session_video_source_version"),
    )
    op.create_index(op.f("ix_annotation_files_id"), "annotation_files", ["id"], unique=False)
    op.create_index("ix_annotation_files_session_video", "annotation_files", ["session_video_id"], unique=False)
    op.create_index(op.f("ix_annotation_files_status"), "annotation_files", ["status"], unique=False)
    op.create_index("ix_annotation_files_source", "annotation_files", ["source"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_annotation_files_source", table_name="annotation_files")
    op.drop_index(op.f("ix_annotation_files_status"), table_name="annotation_files")
    op.drop_index("ix_annotation_files_session_video", table_name="annotation_files")
    op.drop_index(op.f("ix_annotation_files_id"), table_name="annotation_files")
    op.drop_table("annotation_files")

    bind = op.get_bind()
    annotation_file_status.drop(bind, checkfirst=True)
    annotation_source.drop(bind, checkfirst=True)
