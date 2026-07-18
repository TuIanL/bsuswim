# ============================================================
# 迁移脚本 0009：新增视觉资产生成层表
# ============================================================
# 作用：
#   支撑 change `add-kinematics-visual-artifact-generation`
#   - kinematic_artifact_sets：一次完整、可追溯的视觉资产生成结果
#   - kinematic_artifacts：每个图像/图表的资产元数据
#
# 两级结构：ArtifactSet 1—* Artifact，唯一约束分别落在
# (annotation_metric_id, generation_signature) 与 (artifact_set_id, artifact_key)。
# ============================================================

"""add kinematic artifact tables

Revision ID: 20260717_0009
Revises: 20260717_0008
Create Date: 2026-07-17
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260717_0009"
down_revision: Union[str, None] = "20260717_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "kinematic_artifact_sets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "annotation_metric_id",
            sa.Integer(),
            sa.ForeignKey("annotation_metrics.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "normalized_annotation_id",
            sa.Integer(),
            sa.ForeignKey("normalized_annotations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("session_video_id", sa.Integer(), nullable=True),
        sa.Column("schema_version", sa.String(length=50), nullable=False),
        sa.Column("generator", sa.String(length=50), nullable=False),
        sa.Column("generator_version", sa.String(length=50), nullable=False),
        sa.Column("style_profile", sa.String(length=50), nullable=False),
        sa.Column("source_annotation_revision", sa.Integer(), nullable=False),
        sa.Column("source_metric_schema_version", sa.String(length=50), nullable=False),
        sa.Column("source_metric_calculator", sa.String(length=100), nullable=False),
        sa.Column("source_metric_calculator_version", sa.String(length=50), nullable=False),
        sa.Column("source_metric_hash", sa.String(length=64), nullable=False),
        sa.Column("generation_signature", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("manifest", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("manifest_sha256", sa.String(length=64), nullable=True),
        sa.Column("warnings", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_kinematic_artifact_sets_annotation_metric_id",
        "kinematic_artifact_sets",
        ["annotation_metric_id"],
    )
    op.create_index(
        "ix_kinematic_artifact_sets_generation_signature",
        "kinematic_artifact_sets",
        ["generation_signature"],
    )
    op.create_unique_constraint(
        "uq_artifact_set_metric_signature",
        "kinematic_artifact_sets",
        ["annotation_metric_id", "generation_signature"],
    )

    op.create_table(
        "kinematic_artifacts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "artifact_set_id",
            sa.Integer(),
            sa.ForeignKey("kinematic_artifact_sets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("artifact_key", sa.String(length=120), nullable=False),
        sa.Column("artifact_type", sa.String(length=40), nullable=False),
        sa.Column("module_key", sa.String(length=40), nullable=False),
        sa.Column("metric_keys", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("annotation_frame", sa.Integer(), nullable=True),
        sa.Column("source_video_frame", sa.Integer(), nullable=True),
        sa.Column("annotation_frame_range", postgresql.JSONB(), nullable=True),
        sa.Column("source_video_frame_range", postgresql.JSONB(), nullable=True),
        sa.Column("storage_path", sa.String(length=512), nullable=True),
        sa.Column("mime_type", sa.String(length=120), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("skip_reason", sa.String(length=60), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_kinematic_artifacts_artifact_set_id",
        "kinematic_artifacts",
        ["artifact_set_id"],
    )
    op.create_unique_constraint(
        "uq_artifact_set_key",
        "kinematic_artifacts",
        ["artifact_set_id", "artifact_key"],
    )


def downgrade() -> None:
    op.drop_table("kinematic_artifacts")
    op.drop_table("kinematic_artifact_sets")
