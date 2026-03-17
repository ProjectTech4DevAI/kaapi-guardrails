from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

from pydantic import Field, StringConstraints
from sqlmodel import SQLModel

MAX_TOPIC_RELEVANCE_NAME_LENGTH = 100
MAX_TOPIC_RELEVANCE_DESCRIPTION_LENGTH = 500

TopicsName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=MAX_TOPIC_RELEVANCE_NAME_LENGTH,
    ),
]

TopicConfiguration = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
    ),
]


class TopicRelevanceBase(SQLModel):
    name: TopicsName
    description: Optional[str] = None
    prompt_schema_version: int = Field(ge=1)
    configuration: TopicConfiguration


class TopicRelevanceCreate(TopicRelevanceBase):
    pass


class TopicRelevanceUpdate(SQLModel):
    name: Optional[TopicsName] = None
    description: Optional[str] = None
    prompt_schema_version: Optional[int] = Field(default=None, ge=1)
    configuration: Optional[TopicConfiguration] = None
    is_active: Optional[bool] = None


class TopicRelevanceResponse(TopicRelevanceBase):
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
