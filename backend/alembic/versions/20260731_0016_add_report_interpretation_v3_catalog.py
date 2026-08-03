"""add structured interpretation reference catalog"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260731_0016"
down_revision: Union[str, None] = "20260730_0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "report_interpretations",
        sa.Column("reference_catalog", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )


def downgrade() -> None:
    op.drop_column("report_interpretations", "reference_catalog")
