# ============================================================
# 迁移脚本 0010：新增二维运动学复核发现表
# ============================================================
# 作用：
#   支撑 change `add-2d-kinematics-review-findings`
#   - kinematic_review_finding_sets：基于 AnnotationMetric(swim-side-kinematics.v1)
#     生成的待复核发现集合，与 analysis_results 解耦
#
# 唯一约束落在 (annotation_metric_id, generation_signature)。
# ============================================================

"""add kinematic review finding sets

Revision ID: 20260718_0010
Revises: 20260717_0009
Create Date: 2026-07-18
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260718_0010"
down_revision: Union[str, None] = "20260717_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "kinematic_review_finding_sets",
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
            sa.ForeignKey("normalized_annotations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("session_video_id", sa.Integer(), nullable=True),
        sa.Column("schema_version", sa.String(length=50), nullable=False, server_default="swim-2d-review-findings.v1"),
        sa.Column("rule_set", sa.String(length=100), nullable=False),
        sa.Column("rule_version", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("engine_version", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("threshold_basis", sa.String(length=100), nullable=False, server_default="project_heuristic_v1"),
        sa.Column("source_annotation_revision", sa.Integer(), nullable=True),
        sa.Column("source_metric_schema_version", sa.String(length=50), nullable=True),
        sa.Column("source_metric_calculator", sa.String(length=100), nullable=True),
        sa.Column("source_metric_calculator_version", sa.String(length=50), nullable=True),
        sa.Column("source_metric_hash", sa.String(length=128), nullable=True),
        sa.Column("generation_signature", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ready"),
        sa.Column("findings", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("summary", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("skipped_rules", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("warnings", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "annotation_metric_id", "generation_signature", name="uq_review_finding_set_metric_signature"
        ),
    )
    op.create_index("ix_review_finding_set_metric", "kinematic_review_finding_sets", ["annotation_metric_id"])
    op.create_index("ix_review_finding_set_norm_ann", "kinematic_review_finding_sets", ["normalized_annotation_id"])
    op.create_index("ix_review_finding_set_signature", "kinematic_review_finding_sets", ["generation_signature"])
    op.create_index("ix_review_finding_set_metric_hash", "kinematic_review_finding_sets", ["source_metric_hash"])


def downgrade() -> None:
    op.drop_index("ix_review_finding_set_metric_hash", table_name="kinematic_review_finding_sets")
    op.drop_index("ix_review_finding_set_signature", table_name="kinematic_review_finding_sets")
    op.drop_index("ix_review_finding_set_norm_ann", table_name="kinematic_review_finding_sets")
    op.drop_index("ix_review_finding_set_metric", table_name="kinematic_review_finding_sets")
    op.drop_table("kinematic_review_finding_sets")
