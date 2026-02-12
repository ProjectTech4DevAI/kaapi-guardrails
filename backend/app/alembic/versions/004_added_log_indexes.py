"""Added indexes for request_log and validator_log

Revision ID: 004
Revises: 003
Create Date: 2026-02-11 10:45:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: str = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("idx_request_log_request_id", "request_log", ["request_id"])
    op.create_index("idx_request_log_status", "request_log", ["status"])
    op.create_index("idx_request_log_inserted_at", "request_log", ["inserted_at"])

    op.create_index("idx_validator_log_request_id", "validator_log", ["request_id"])
    op.create_index("idx_validator_log_inserted_at", "validator_log", ["inserted_at"])
    op.create_index("idx_validator_log_outcome", "validator_log", ["outcome"])
    op.create_index("idx_validator_log_name", "validator_log", ["name"])


def downgrade() -> None:
    op.drop_index("idx_validator_log_inserted_at", table_name="validator_log")
    op.drop_index("idx_validator_log_request_id", table_name="validator_log")
    op.drop_index("idx_validator_log_outcome", table_name="validator_log")
    op.drop_index("idx_validator_log_name", table_name="validator_log")

    op.drop_index("idx_request_log_inserted_at", table_name="request_log")
    op.drop_index("idx_request_log_status", table_name="request_log")
    op.drop_index("idx_request_log_request_id", table_name="request_log")
