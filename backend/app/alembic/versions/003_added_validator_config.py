"""Added validator_config table

Revision ID: 003
Revises: 002
Create Date: 2026-02-05 09:42:54.128852

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects import postgresql
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: str = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "validator_config",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("stage", sa.String(), nullable=False),
        sa.Column("on_fail_action", sa.String(), nullable=False),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "project_id",
            "type",
            "stage",
            name="uq_validator_identity",
        ),
    )

    op.create_index(
        "idx_validator_organization", "validator_config", ["organization_id"]
    )
    op.create_index("idx_validator_project", "validator_config", ["project_id"])
    op.create_index("idx_validator_type", "validator_config", ["type"])
    op.create_index("idx_validator_stage", "validator_config", ["stage"])


def downgrade() -> None:
    op.drop_table("validator_config")
