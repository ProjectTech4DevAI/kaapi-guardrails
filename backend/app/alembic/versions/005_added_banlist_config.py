"""Added ban_list table

Revision ID: 005
Revises: 004
Create Date: 2026-02-05 09:42:54.128852

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects import postgresql
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ban_list",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("domain", sa.String(), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "banned_words",
            postgresql.ARRAY(sa.String(length=100)),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "name", "organization_id", "project_id", name="uq_banlist_name_org_project"
        ),
        sa.CheckConstraint(
            "coalesce(array_length(banned_words, 1), 0) <= 1000",
            name="ck_banlist_banned_words_max_items",
        ),
    )

    op.create_index("idx_banlist_organization", "ban_list", ["organization_id"])
    op.create_index("idx_banlist_project", "ban_list", ["project_id"])
    op.create_index("idx_banlist_domain", "ban_list", ["domain"])
    op.create_index("idx_banlist_is_public", "ban_list", ["is_public"])


def downgrade() -> None:
    op.drop_table("ban_list")
