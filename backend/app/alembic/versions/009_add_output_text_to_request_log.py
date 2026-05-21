"""Add output_text to request_log

Revision ID: 009
Revises: 008
Create Date: 2026-05-21 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009"
down_revision = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "request_log",
        sa.Column("output_text", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("request_log", "output_text")
