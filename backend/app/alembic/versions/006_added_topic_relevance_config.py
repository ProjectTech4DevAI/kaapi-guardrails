"""Added topic_relevance table

Revision ID: 006
Revises: 005
Create Date: 2026-03-05 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "topic_relevance",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("prompt_version", sa.Integer(), nullable=False),
        sa.Column(
            "configuration", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "name",
            "organization_id",
            "project_id",
            name="uq_topic_relevance_name_org_project",
        ),
    )

    op.create_index(
        "idx_topic_relevance_organization", "topic_relevance", ["organization_id"]
    )
    op.create_index("idx_topic_relevance_project", "topic_relevance", ["project_id"])
    op.create_index(
        "idx_topic_relevance_prompt_version", "topic_relevance", ["prompt_version"]
    )
    op.create_index("idx_topic_relevance_is_active", "topic_relevance", ["is_active"])


def downgrade() -> None:
    op.drop_table("topic_relevance")
