from typing import Optional, Dict
from uuid import UUID, uuid4
from datetime import datetime

from sqlmodel import SQLModel, Field
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB


class TopicRelevancePreset(SQLModel, table=True):
    __tablename__ = "topic_relevance_presets"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    organization_id: int = Field(index=True)
    project_id: int = Field(index=True)

    name: str
    description: Optional[str] = None

    preset_schema_version: int = Field(default=1, index=True)

    preset_payload: Dict = Field(sa_column=Column(JSONB, nullable=False))

    is_active: bool = Field(default=True, index=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
