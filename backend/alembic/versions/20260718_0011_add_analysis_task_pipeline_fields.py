# ============================================================
# 迁移脚本 0011：AnalysisTask 多 pipeline 执行字段
# ============================================================
# 作用：
#   支撑 change `add-annotation-driven-analysis-pipeline`
#   - pipeline_type / pipeline_version：任务路由
#   - execution_state：可变执行状态与检查点（JSON）
#   - attempt_count：重试计数
#   - failed_stage / error_code：结构化失败信息
#
# 现有任务回填为 model_service / model_service_v1。
# ============================================================

"""add analysis task pipeline execution fields

Revision ID: 20260718_0011
Revises: 20260718_0010
Create Date: 2026-07-18
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260718_0011"
down_revision: Union[str, None] = "20260718_0010"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column(
        "analysis_tasks",
        sa.Column("pipeline_type", sa.String(40), nullable=False, server_default="model_service"),
    )
    op.add_column(
        "analysis_tasks",
        sa.Column("pipeline_version", sa.String(50), nullable=False, server_default="model_service_v1"),
    )
    op.add_column(
        "analysis_tasks",
        sa.Column("execution_state", sa.JSON, nullable=False, server_default=sa.text("'{}'")),
    )
    op.add_column(
        "analysis_tasks",
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column("analysis_tasks", sa.Column("failed_stage", sa.String(80), nullable=True))
    op.add_column("analysis_tasks", sa.Column("error_code", sa.String(100), nullable=True))

    op.execute("UPDATE analysis_tasks SET pipeline_type='model_service', pipeline_version='model_service_v1' WHERE pipeline_type IS NULL OR pipeline_type=''")
    op.execute("ALTER TABLE analysis_tasks ALTER COLUMN pipeline_type DROP DEFAULT")
    op.execute("ALTER TABLE analysis_tasks ALTER COLUMN pipeline_version DROP DEFAULT")
    op.execute("ALTER TABLE analysis_tasks ALTER COLUMN execution_state DROP DEFAULT")
    op.execute("ALTER TABLE analysis_tasks ALTER COLUMN attempt_count DROP DEFAULT")


def downgrade() -> None:
    op.drop_column("analysis_tasks", "error_code")
    op.drop_column("analysis_tasks", "failed_stage")
    op.drop_column("analysis_tasks", "attempt_count")
    op.drop_column("analysis_tasks", "execution_state")
    op.drop_column("analysis_tasks", "pipeline_version")
    op.drop_column("analysis_tasks", "pipeline_type")
