"""add manual temporal reference labels

Revision ID: 20260907_0017
Revises: 20260731_0016
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260907_0017"
down_revision: Union[str, None] = "20260731_0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 注意：sets.head_revision_id → revisions.id 与 revisions.set_id → sets.id 互相引用，
    # 建表时 MUST 先让其中一个不带 FK，建完再补（否则 PostgreSQL 报 relation does not exist）。
    # ── manual_annotation_sets（谱系，先建，head_revision_id FK 稍后补）──
    op.create_table(
        "manual_annotation_sets",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("session_video_id", sa.Integer(), sa.ForeignKey("session_videos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("phase_profile_id", sa.String(length=80), nullable=False),
        sa.Column("head_revision_id", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Index("ix_manual_annotation_sets_session_video_id", "session_video_id"),
    )

    # ── manual_annotation_revisions（不可变版本 + 可复现快照）──
    op.create_table(
        "manual_annotation_revisions",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("set_id", sa.Integer(), sa.ForeignKey("manual_annotation_sets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("forked_from_revision_id", sa.Integer(), nullable=True),
        sa.Column("video_checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("video_fps_snapshot", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("video_duration_snapshot", sa.Numeric(precision=10, scale=3), nullable=True),
        sa.Column("frame_basis", sa.JSON(), nullable=True),
        sa.Column("phase_profile_id", sa.String(length=80), nullable=False),
        sa.Column("phase_profile_version", sa.String(length=40), nullable=False),
        sa.Column("phase_profile_hash", sa.String(length=64), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="draft", nullable=False),
        sa.Column("segment_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("cycle_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("edit_version", sa.Integer(), server_default="0", nullable=False),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("review_status", sa.String(length=20), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["forked_from_revision_id"], ["manual_annotation_revisions.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint("set_id", "revision_no", name="uq_annotation_set_revision_no"),
        # 注意：MUST NOT 建立 UNIQUE(set_id, content_hash)，fork 内容相同会违反。
        sa.Index("ix_manual_annotation_revisions_set_revision_no", "set_id", "revision_no"),
        sa.Index("ix_manual_annotation_revisions_content_hash", "content_hash"),
        sa.Index("ix_manual_annotation_revisions_profile_hash", "phase_profile_hash"),
    )

    # ── manual_phase_segments（区间行，仅 revision_id 归属）──
    op.create_table(
        "manual_phase_segments",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("revision_id", sa.Integer(), sa.ForeignKey("manual_annotation_revisions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cycle_id", sa.String(length=36), nullable=False),
        sa.Column("cycle_index", sa.Integer(), nullable=True),
        sa.Column("side", sa.String(length=10), nullable=False),
        sa.Column("phase_code", sa.String(length=20), nullable=False),
        sa.Column("start_time_sec", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("end_time_sec", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("start_frame", sa.Integer(), nullable=True),
        sa.Column("end_frame", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("derivation", sa.String(length=20), server_default="manual", nullable=False),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("review_status", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "revision_id", "cycle_id", "side", "phase_code",
            name="uq_segment_revision_cycle_side_phase",
        ),
        # segment 表无 set_id 列，禁止建 (set_id, revision_id) 索引。
        sa.Index("ix_manual_phase_segments_revision_id", "revision_id"),
        sa.Index("ix_manual_phase_segments_revision_side", "revision_id", "side"),
        sa.Index("ix_manual_phase_segments_revision_cycle", "revision_id", "cycle_id"),
        sa.Index("ix_manual_phase_segments_revision_side_cycle", "revision_id", "side", "cycle_id"),
    )

    # ── 补 sets.head_revision_id → revisions.id（revisions 已存在）──
    op.create_foreign_key(
        "fk_manual_annotation_sets_head_revision",
        "manual_annotation_sets",
        "manual_annotation_revisions",
        ["head_revision_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # ── analysis_tasks 增加显式引用 FK（先建表后加列，保证 FK 目标已存在）──
    op.add_column(
        "analysis_tasks",
        sa.Column("reference_annotation_revision_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_analysis_tasks_reference_revision",
        "analysis_tasks",
        "manual_annotation_revisions",
        ["reference_annotation_revision_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_analysis_tasks_reference_annotation_revision_id",
        "analysis_tasks",
        ["reference_annotation_revision_id"],
    )


def downgrade() -> None:
    # 顺序至关重要，否则 PostgreSQL 会因 FK 依赖拒绝删表：
    # ① 解除 analysis_tasks 的 FK 并删列 → ② 解除 sets.head_revision_id 对 revisions 的 FK
    # ③ 删 segments → ④ 删 revisions → ⑤ 删 sets
    op.drop_index("ix_analysis_tasks_reference_annotation_revision_id", table_name="analysis_tasks")
    op.drop_constraint("fk_analysis_tasks_reference_revision", "analysis_tasks", type_="foreignkey")
    op.drop_column("analysis_tasks", "reference_annotation_revision_id")

    op.drop_constraint("fk_manual_annotation_sets_head_revision", "manual_annotation_sets", type_="foreignkey")

    op.drop_table("manual_phase_segments")
    op.drop_table("manual_annotation_revisions")
    op.drop_table("manual_annotation_sets")
