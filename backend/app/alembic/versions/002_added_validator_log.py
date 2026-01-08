"""Added validator log

Revision ID: 6edf37b70db4
Revises: 001
Create Date: 2026-01-07 09:43:48.002351

"""
from typing import Sequence, Union

from alembic import op
import sqlmodel
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, Sequence[str], None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('validator_log',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('request_id', sa.Uuid(), nullable=False),
    sa.Column('input', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('output', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('error', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('inserted_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['request_id'], ['request_log.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('validator_log')
