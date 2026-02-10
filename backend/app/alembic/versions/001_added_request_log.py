"""Added request log

Revision ID: 001
Revises: 
Create Date: 2026-01-07 09:42:54.128852

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "request_log",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("response_id", sa.Uuid(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("PROCESSING", "SUCCESS", "ERROR", "WARNING", name="requeststatus"),
            nullable=False,
            default="PROCESSING",
        ),
        sa.Column("request_text", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("response_text", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("inserted_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("request_log")
    # todo : drop requeststatus enum type
