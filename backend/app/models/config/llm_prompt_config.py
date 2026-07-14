from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.enum import LLMValidatorName
from app.utils import now


class LLMPromptConfig(SQLModel, table=True):
    __tablename__ = "llm_prompt"

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        sa_column_kwargs={"comment": "Unique identifier for the LLM prompt config"},
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

    validator_name: LLMValidatorName = Field(
        nullable=False,
        index=True,
        sa_column_kwargs={"comment": "Validator type this prompt config belongs to"},
    )

    name: str = Field(
        nullable=False,
        sa_column_kwargs={"comment": "Human-readable name for this prompt config"},
    )

    description: str = Field(
        nullable=False,
        sa_column_kwargs={"comment": "Description of what this prompt evaluates"},
    )

    prompt_schema_version: int = Field(
        default=1,
        index=True,
        nullable=False,
        sa_column_kwargs={"comment": "Version of the prompt schema"},
    )

    llm_prompt: str = Field(
        nullable=False,
        sa_column_kwargs={"comment": "Prompt text used by the LLM validator"},
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

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "project_id",
            "validator_name",
            "prompt_schema_version",
            "llm_prompt",
            name="uq_llm_prompt_config",
        ),
    )
