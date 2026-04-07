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
        SET name = 'config_' || id::text
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
    # If your table has multiple configs of a specific validator and type combination it will be hard to downgrade the change
    # manually delete the configurations and keep the one that won't give an error during downgrade
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM validator_config
                GROUP BY organization_id, project_id, type, stage
                HAVING COUNT(*) > 1
            ) THEN
                RAISE EXCEPTION
                    'Cannot downgrade revision 007: duplicate validator_config rows exist for (organization_id, project_id, type, stage). Resolve them manually first.';
            END IF;
        END
        $$;
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
