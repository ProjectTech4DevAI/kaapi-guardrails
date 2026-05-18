"""Add answer_relevance_prompt table

Revision ID: 008
Revises: 007
Create Date: 2026-05-08 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "answer_relevance_prompt",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("prompt_template", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "idx_answer_relevance_prompt_org",
        "answer_relevance_prompt",
        ["organization_id"],
    )
    op.create_index(
        "idx_answer_relevance_prompt_project",
        "answer_relevance_prompt",
        ["project_id"],
    )
    op.create_index(
        "idx_answer_relevance_prompt_is_active",
        "answer_relevance_prompt",
        ["is_active"],
    )


def downgrade() -> None:
    op.drop_table("answer_relevance_prompt")
