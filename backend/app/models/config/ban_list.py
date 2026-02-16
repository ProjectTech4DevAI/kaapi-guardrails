from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlmodel import Field, SQLModel

from app.utils import now


class BanList(SQLModel, table=True):
    __tablename__ = "ban_list"

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        sa_column_kwargs={"comment": "Unique identifier for the ban list entry"},
    )

    name: str = Field(
        nullable=False, sa_column_kwargs={"comment": "Name of the ban list entry"}
    )

    description: str = Field(
        nullable=False,
        sa_column_kwargs={"comment": "Description of the ban list entry"},
    )

    banned_words: list[str] = Field(
        default_factory=list,
        sa_column=Column(
            ARRAY(String),
            nullable=False,
            comment="List of banned words",
        ),
        description=("List of banned words"),
    )

    organization_id: int = Field(
        nullable=False,
        sa_column_kwargs={"comment": "Identifier for the organization"},
    )

    project_id: int = Field(
        nullable=False,
        sa_column_kwargs={"comment": "Identifier for the project"},
    )

    domain: str = Field(
        nullable=False,
        sa_column_kwargs={"comment": "Domain or context for the ban list entry"},
    )

    is_public: bool = Field(
        default=False,
        sa_column_kwargs={"comment": "Whether the ban list entry is public or private"},
    )

    created_at: datetime = Field(
        default_factory=now,
        nullable=False,
        sa_column_kwargs={"comment": "Timestamp when the ban list entry was created"},
    )

    updated_at: datetime = Field(
        default_factory=now,
        nullable=False,
        sa_column_kwargs={
            "comment": "Timestamp when the ban list entry was last updated",
            "onupdate": now,
        },
    )
