"""Rename validator_log.request_id to request_log_id

The column is a foreign key to request_log.id (the surrogate PK), not to
request_log.request_id (the caller-supplied business id) - the old name
made it easy to join on the wrong column.

Revision ID: 011
Revises: 010
Create Date: 2026-09-04 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("validator_log", "request_id", new_column_name="request_log_id")
    op.execute(
        "ALTER INDEX idx_validator_log_request_id RENAME TO idx_validator_log_request_log_id"
    )


def downgrade() -> None:
    op.execute(
        "ALTER INDEX idx_validator_log_request_log_id RENAME TO idx_validator_log_request_id"
    )
    op.alter_column("validator_log", "request_log_id", new_column_name="request_id")
