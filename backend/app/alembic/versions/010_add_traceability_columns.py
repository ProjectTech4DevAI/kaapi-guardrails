"""Add traceability columns to request_log and validator_log

Revision ID: 010
Revises: 009
Create Date: 2026-08-25 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "010"
down_revision = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "request_log",
        sa.Column(
            "metadata",
            JSONB,
            nullable=True,
            comment="Full run_guardrails request payload",
        ),
    )
    op.add_column(
        "validator_log",
        sa.Column(
            "order",
            sa.Integer(),
            nullable=True,
            comment="1-based execution order of the validator within the request",
        ),
    )
    op.add_column(
        "validator_log",
        sa.Column(
            "stage",
            sa.String(),
            nullable=True,
            comment="Stage the validator checked (input or output)",
        ),
    )
    op.add_column(
        "validator_log",
        sa.Column(
            "type",
            sa.String(),
            nullable=True,
            comment="Validator type (ValidatorType enum value)",
        ),
    )
    op.add_column(
        "validator_log",
        sa.Column(
            "family",
            sa.String(),
            nullable=True,
            comment="Validator family (lexical, classifier or semantic)",
        ),
    )
    op.add_column(
        "validator_log",
        sa.Column(
            "metadata",
            JSONB,
            nullable=True,
            comment="Full resolved validator config used for this run",
        ),
    )


def downgrade() -> None:
    op.drop_column("validator_log", "metadata")
    op.drop_column("validator_log", "family")
    op.drop_column("validator_log", "type")
    op.drop_column("validator_log", "stage")
    op.drop_column("validator_log", "order")
    op.drop_column("request_log", "metadata")
