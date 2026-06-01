from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import StringConstraints, model_validator
from sqlmodel import Field, SQLModel

from app.core.enum import LLMValidatorName

MAX_NAME_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 500

LLMPromptName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_NAME_LENGTH),
]

LLMPromptDescription = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=1, max_length=MAX_DESCRIPTION_LENGTH
    ),
]

LLMPromptText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]

_ANSWER_RELEVANCE_PLACEHOLDERS = ("{query}", "{answer}")


class LLMPromptConfigCreate(SQLModel):
    validator_name: LLMValidatorName
    name: LLMPromptName
    description: LLMPromptDescription
    prompt_schema_version: int = Field(default=1, ge=1)
    llm_prompt: LLMPromptText

    @model_validator(mode="after")
    def validate_answer_relevance_placeholders(self) -> "LLMPromptConfigCreate":
        if self.validator_name == LLMValidatorName.AnswerRelevanceCustomLLM:
            missing = [
                p for p in _ANSWER_RELEVANCE_PLACEHOLDERS if p not in self.llm_prompt
            ]
            if missing:
                raise ValueError(
                    f"llm_prompt must contain the placeholders: {', '.join(missing)}"
                )
        return self


class LLMPromptConfigUpdate(SQLModel):
    name: LLMPromptName | None = None
    description: LLMPromptDescription | None = None
    prompt_schema_version: int | None = Field(default=None, ge=1)
    llm_prompt: LLMPromptText | None = None
    is_active: bool | None = None


class LLMPromptConfigResponse(SQLModel):
    id: UUID
    validator_name: LLMValidatorName
    name: str
    description: str
    prompt_schema_version: int
    llm_prompt: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
