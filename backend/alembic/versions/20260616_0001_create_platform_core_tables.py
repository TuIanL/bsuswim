"""create platform core tables

Revision ID: 20260616_0001
Revises:
Create Date: 2026-06-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260616_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


analysis_task_status = postgresql.ENUM(
    "UPLOADED",
    "QUEUED",
    "PROCESSING",
    "RESULT_SAVING",
    "COMPLETED",
    "FAILED",
    name="analysistaskstatus",
    create_type=False,
)
stroke_type = postgresql.ENUM(
    "FREESTYLE",
    "BREASTSTROKE",
    "BACKSTROKE",
    "BUTTERFLY",
    "MIXED",
    name="stroketype",
    create_type=False,
)
training_session_status = postgresql.ENUM(
    "DRAFT",
    "VIDEO_UPLOADED",
    "ANALYZING",
    "COMPLETED",
    "FAILED",
    name="trainingsessionstatus",
    create_type=False,
)
user_role = postgresql.ENUM("ADMIN", "COACH", "ATHLETE", name="userrole", create_type=False)
view_type = postgresql.ENUM("SIDE", "FRONT", "TOP", "UNDERWATER", "OTHER", name="viewtype", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    analysis_task_status.create(bind, checkfirst=True)
    stroke_type.create(bind, checkfirst=True)
    training_session_status.create(bind, checkfirst=True)
    user_role.create(bind, checkfirst=True)
    view_type.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=80), nullable=True),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_phone"), "users", ["phone"], unique=True)

    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("team_type", sa.String(length=40), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_teams_id"), "teams", ["id"], unique=False)

    op.create_table(
        "video_files",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stored_filename"),
    )
    op.create_index(op.f("ix_video_files_id"), "video_files", ["id"], unique=False)

    op.create_table(
        "athletes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("gender", sa.String(length=20), nullable=True),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("height_cm", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("weight_kg", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("stroke_specialty", sa.String(length=40), nullable=True),
        sa.Column("level", sa.String(length=40), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("coach_id", sa.Integer(), nullable=True),
        sa.Column("team_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["coach_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_athletes_id"), "athletes", ["id"], unique=False)
    op.create_index(op.f("ix_athletes_coach_id"), "athletes", ["coach_id"], unique=False)
    op.create_index(op.f("ix_athletes_team_id"), "athletes", ["team_id"], unique=False)

    op.create_table(
        "training_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("athlete_id", sa.Integer(), nullable=False),
        sa.Column("coach_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("session_date", sa.Date(), nullable=True),
        sa.Column("venue", sa.String(length=120), nullable=True),
        sa.Column("stroke_type", stroke_type, nullable=False),
        sa.Column("distance_m", sa.Integer(), nullable=True),
        sa.Column("pool_length_m", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("status", training_session_status, nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"]),
        sa.ForeignKeyConstraint(["coach_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_training_sessions_id"), "training_sessions", ["id"], unique=False)
    op.create_index(op.f("ix_training_sessions_athlete_id"), "training_sessions", ["athlete_id"], unique=False)
    op.create_index(op.f("ix_training_sessions_coach_id"), "training_sessions", ["coach_id"], unique=False)
    op.create_index(op.f("ix_training_sessions_status"), "training_sessions", ["status"], unique=False)

    op.create_table(
        "session_videos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("video_file_id", sa.Integer(), nullable=False),
        sa.Column("view_type", view_type, nullable=False),
        sa.Column("fps", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("resolution", sa.String(length=40), nullable=True),
        sa.Column("sync_offset_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["training_sessions.id"]),
        sa.ForeignKeyConstraint(["video_file_id"], ["video_files.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "video_file_id", name="uq_session_video_file"),
    )
    op.create_index(op.f("ix_session_videos_id"), "session_videos", ["id"], unique=False)
    op.create_index(op.f("ix_session_videos_session_id"), "session_videos", ["session_id"], unique=False)
    op.create_index(op.f("ix_session_videos_video_file_id"), "session_videos", ["video_file_id"], unique=False)

    op.create_table(
        "analysis_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("status", analysis_task_status, nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("stage", sa.String(length=80), nullable=False),
        sa.Column("request_payload", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["training_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_analysis_tasks_id"), "analysis_tasks", ["id"], unique=False)
    op.create_index(op.f("ix_analysis_tasks_session_id"), "analysis_tasks", ["session_id"], unique=False)
    op.create_index(op.f("ix_analysis_tasks_status"), "analysis_tasks", ["status"], unique=False)

    op.create_table(
        "analysis_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        sa.Column("detections", sa.JSON(), nullable=False),
        sa.Column("keypoint_frames", sa.JSON(), nullable=False),
        sa.Column("phases", sa.JSON(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("diagnostics", sa.JSON(), nullable=False),
        sa.Column("raw_result", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["analysis_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id"),
    )
    op.create_index(op.f("ix_analysis_results_id"), "analysis_results", ["id"], unique=False)

    op.create_table(
        "report_metadata",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("report_data", sa.JSON(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["training_sessions.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["analysis_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", name="uq_report_session"),
        sa.UniqueConstraint("task_id"),
    )
    op.create_index(op.f("ix_report_metadata_id"), "report_metadata", ["id"], unique=False)
    op.create_index(op.f("ix_report_metadata_session_id"), "report_metadata", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_report_metadata_session_id"), table_name="report_metadata")
    op.drop_index(op.f("ix_report_metadata_id"), table_name="report_metadata")
    op.drop_table("report_metadata")
    op.drop_index(op.f("ix_analysis_results_id"), table_name="analysis_results")
    op.drop_table("analysis_results")
    op.drop_index(op.f("ix_analysis_tasks_status"), table_name="analysis_tasks")
    op.drop_index(op.f("ix_analysis_tasks_session_id"), table_name="analysis_tasks")
    op.drop_index(op.f("ix_analysis_tasks_id"), table_name="analysis_tasks")
    op.drop_table("analysis_tasks")
    op.drop_index(op.f("ix_session_videos_video_file_id"), table_name="session_videos")
    op.drop_index(op.f("ix_session_videos_session_id"), table_name="session_videos")
    op.drop_index(op.f("ix_session_videos_id"), table_name="session_videos")
    op.drop_table("session_videos")
    op.drop_index(op.f("ix_training_sessions_status"), table_name="training_sessions")
    op.drop_index(op.f("ix_training_sessions_coach_id"), table_name="training_sessions")
    op.drop_index(op.f("ix_training_sessions_athlete_id"), table_name="training_sessions")
    op.drop_index(op.f("ix_training_sessions_id"), table_name="training_sessions")
    op.drop_table("training_sessions")
    op.drop_index(op.f("ix_athletes_team_id"), table_name="athletes")
    op.drop_index(op.f("ix_athletes_coach_id"), table_name="athletes")
    op.drop_index(op.f("ix_athletes_id"), table_name="athletes")
    op.drop_table("athletes")
    op.drop_index(op.f("ix_video_files_id"), table_name="video_files")
    op.drop_table("video_files")
    op.drop_index(op.f("ix_teams_id"), table_name="teams")
    op.drop_table("teams")
    op.drop_index(op.f("ix_users_phone"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    view_type.drop(bind, checkfirst=True)
    user_role.drop(bind, checkfirst=True)
    training_session_status.drop(bind, checkfirst=True)
    stroke_type.drop(bind, checkfirst=True)
    analysis_task_status.drop(bind, checkfirst=True)
