"""Added llm_validator_prompt: rename topic_relevance to llm_prompt, add validator_name, rename configuration to llm_prompt

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
    # Rename table
    op.rename_table("topic_relevance", "llm_prompt")

    # Rename indexes created by migration 006
    op.execute(
        "ALTER INDEX idx_topic_relevance_organization RENAME TO idx_llm_prompt_organization"
    )
    op.execute(
        "ALTER INDEX idx_topic_relevance_project RENAME TO idx_llm_prompt_project"
    )
    op.execute(
        "ALTER INDEX idx_topic_relevance_prompt_schema_version "
        "RENAME TO idx_llm_prompt_prompt_schema_version"
    )
    op.execute(
        "ALTER INDEX idx_topic_relevance_is_active RENAME TO idx_llm_prompt_is_active"
    )

    # Add validator_name column (backfill existing rows as topic_relevance)
    op.add_column(
        "llm_prompt",
        sa.Column(
            "validator_name",
            sa.String(),
            nullable=False,
            server_default="topic_relevance",
        ),
    )

    # Rename configuration → llm_prompt column
    op.alter_column("llm_prompt", "configuration", new_column_name="llm_prompt")

    # Replace unique constraint to include validator_name and use new column name
    op.drop_constraint(
        "uq_topic_relevance_config_org_project_prompt",
        "llm_prompt",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_llm_prompt_config",
        "llm_prompt",
        [
            "organization_id",
            "project_id",
            "validator_name",
            "prompt_schema_version",
            "llm_prompt",
        ],
    )

    op.create_index("idx_llm_prompt_validator_name", "llm_prompt", ["validator_name"])


def downgrade() -> None:
    op.drop_index("idx_llm_prompt_validator_name", table_name="llm_prompt")

    op.drop_constraint("uq_llm_prompt_config", "llm_prompt", type_="unique")
    op.create_unique_constraint(
        "uq_topic_relevance_config_org_project_prompt",
        "llm_prompt",
        ["organization_id", "project_id", "prompt_schema_version", "llm_prompt"],
    )

    op.alter_column("llm_prompt", "llm_prompt", new_column_name="configuration")

    op.drop_column("llm_prompt", "validator_name")

    op.execute(
        "ALTER INDEX idx_llm_prompt_is_active RENAME TO idx_topic_relevance_is_active"
    )
    op.execute(
        "ALTER INDEX idx_llm_prompt_prompt_schema_version "
        "RENAME TO idx_topic_relevance_prompt_schema_version"
    )
    op.execute(
        "ALTER INDEX idx_llm_prompt_project RENAME TO idx_topic_relevance_project"
    )
    op.execute(
        "ALTER INDEX idx_llm_prompt_organization RENAME TO idx_topic_relevance_organization"
    )

    op.rename_table("llm_prompt", "topic_relevance")
