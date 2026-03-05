from uuid import UUID, uuid4
from datetime import datetime

from sqlmodel import SQLModel, Field

from app.utils import now


class TopicRelevance(SQLModel, table=True):
    __tablename__ = "topic_relevance"

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        sa_column_kwargs={"comment": "Unique identifier for the topic relevance entry"},
    )

    organization_id: int = Field(
        nullable=False,
        index=True,
        sa_column_kwargs={"comment": "Identifier for the organization"},
    )

    project_id: int = Field(
        nullable=False,
        index=True,
        sa_column_kwargs={"comment": "Identifier for the project"},
    )

    name: str = Field(
        nullable=False,
        sa_column_kwargs={"comment": "Name of the topic relevance entry"},
    )

    description: str = Field(
        nullable=True,
        sa_column_kwargs={"comment": "Description of the topic relevance entry"},
    )

    prompt_schema_version: int = Field(
        index=True,
        nullable=False,
        sa_column_kwargs={"comment": "Version of the topic relevance prompt to use"},
    )

    configuration: str = Field(
        nullable=False,
        sa_column_kwargs={
            "comment": "Prompt text blob containing topic relevance scope definition"
        },
    )

    is_active: bool = Field(
        default=True,
        index=True,
        sa_column_kwargs={
            "comment": "Whether the topic relevance entry is active or not"
        },
    )

    created_at: datetime = Field(
        default_factory=now,
        nullable=False,
        sa_column_kwargs={
            "comment": "Timestamp when the topic configuration entry was created"
        },
    )

    updated_at: datetime = Field(
        default_factory=now,
        nullable=False,
        sa_column_kwargs={
            "comment": "Timestamp when the topic configuration entry was last updated",
            "onupdate": now,
        },
    )
