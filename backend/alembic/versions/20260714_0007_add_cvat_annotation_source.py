"""add cvat to annotationsource enum

Revision ID: 20260714_0007
Revises: 20260709_0006
Create Date: 2026-07-14
"""
from typing import Sequence, Union

from alembic import op

revision: str = "20260714_0007"
down_revision: Union[str, None] = "20260709_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TYPE annotationsource "
            "ADD VALUE IF NOT EXISTS 'cvat'"
        )


def downgrade() -> None:
    # PostgreSQL 不支持安全移除 enum value。
    # 该 migration 是前向兼容的数据类型扩展，不可逆。
    pass
