from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel

from app.utils import now


class AnswerRelevancePrompt(SQLModel, table=True):
    __tablename__ = "answer_relevance_prompt"

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        sa_column_kwargs={"comment": "Unique identifier for the prompt config"},
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
        sa_column_kwargs={"comment": "Human-readable name for this prompt config"},
    )

    description: str = Field(
        nullable=False,
        sa_column_kwargs={"comment": "Description of what this prompt evaluates"},
    )

    # Must contain {query} and {answer} placeholders.
    prompt_template: str = Field(
        nullable=False,
        sa_column_kwargs={
            "comment": "Prompt template with {query} and {answer} placeholders"
        },
    )

    is_active: bool = Field(
        default=True,
        index=True,
        nullable=False,
        sa_column_kwargs={"comment": "Whether this prompt config is active"},
    )

    created_at: datetime = Field(
        default_factory=now,
        nullable=False,
        sa_column_kwargs={"comment": "Timestamp when the entry was created"},
    )

    updated_at: datetime = Field(
        default_factory=now,
        nullable=False,
        sa_column_kwargs={
            "comment": "Timestamp when the entry was last updated",
            "onupdate": now,
        },
    )
