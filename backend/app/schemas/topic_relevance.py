from datetime import datetime
from typing import Annotated, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, StringConstraints

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


class TopicRelevanceBase(BaseModel):
    name: TopicsName
    description: Optional[str] = None
    prompt_version: int
    configuration: Dict


class TopicRelevanceCreate(TopicRelevanceBase):
    pass


class TopicRelevanceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    prompt_version: Optional[int] = None
    configuration: Optional[Dict] = None
    is_active: Optional[bool] = None


class TopicRelevanceResponse(TopicRelevanceBase):
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
