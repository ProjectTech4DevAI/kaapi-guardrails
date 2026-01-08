"""Added request log

Revision ID: 45c2306d1868
Revises: 
Create Date: 2026-01-07 09:42:54.128852

"""
from typing import Sequence, Union

from alembic import op
import sqlmodel
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('request_log',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('request_id', sa.Uuid(), nullable=False),
    sa.Column('response_id', sa.Uuid(), nullable=True),
    sa.Column('status', sa.Enum('PROCESSING','SUCCESS', 'ERROR', 'WARNING', name='requeststatus'), nullable=False, default='PROCESSING'),
    sa.Column('request_text', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('response_text', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('inserted_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('request_log')
    # todo : drop requeststatus enum type

