"""Add name column to validator_config and update unique constraint

Revision ID: 007
Revises: 006
Create Date: 2026-03-25 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: str = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "validator_config",
        sa.Column("name", sa.String(), nullable=True),
    )
    op.execute(
        """
        UPDATE validator_config
        SET name = 'config_' || (extract(epoch from created_at) * 1000)::bigint::text
        WHERE name IS NULL
    """
    )

    op.alter_column("validator_config", "name", nullable=False)
    op.drop_constraint("uq_validator_identity", "validator_config", type_="unique")
    op.create_unique_constraint(
        "uq_validator_name",
        "validator_config",
        ["organization_id", "project_id", "name"],
    )
    op.create_index("idx_validator_name", "validator_config", ["name"])


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM validator_config
        WHERE id IN (
            SELECT id
            FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY organization_id, project_id, type, stage
                           ORDER BY created_at ASC, id
                       ) as row_num
                FROM validator_config
            ) ranked
            WHERE row_num > 1
        )
    """
    )

    op.drop_index("idx_validator_name", table_name="validator_config")
    op.drop_constraint("uq_validator_name", "validator_config", type_="unique")
    op.create_unique_constraint(
        "uq_validator_identity",
        "validator_config",
        ["organization_id", "project_id", "type", "stage"],
    )
    op.drop_column("validator_config", "name")
