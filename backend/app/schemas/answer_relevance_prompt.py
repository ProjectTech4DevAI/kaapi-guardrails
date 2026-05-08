from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

from pydantic import StringConstraints, field_validator
from sqlmodel import Field, SQLModel

MAX_NAME_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 500

PromptName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_NAME_LENGTH),
]

PromptDescription = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=1, max_length=MAX_DESCRIPTION_LENGTH
    ),
]

PromptTemplate = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]


def _validate_placeholders(value: str) -> str:
    missing = [p for p in ("{query}", "{answer}") if p not in value]
    if missing:
        raise ValueError(
            f"prompt_template must contain the placeholders: {', '.join(missing)}"
        )
    return value


class AnswerRelevancePromptBase(SQLModel):
    name: PromptName
    description: PromptDescription
    prompt_template: PromptTemplate

    @field_validator("prompt_template")
    @classmethod
    def check_placeholders(cls, v: str) -> str:
        return _validate_placeholders(v)


class AnswerRelevancePromptCreate(AnswerRelevancePromptBase):
    pass


class AnswerRelevancePromptUpdate(SQLModel):
    name: Optional[PromptName] = None
    description: Optional[PromptDescription] = None
    prompt_template: Optional[PromptTemplate] = None
    is_active: Optional[bool] = None

    @field_validator("prompt_template")
    @classmethod
    def check_placeholders(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return _validate_placeholders(v)
        return v


class AnswerRelevancePromptResponse(AnswerRelevancePromptBase):
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
