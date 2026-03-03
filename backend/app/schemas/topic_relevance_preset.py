from typing import Dict, Optional
from uuid import UUID
from pydantic import BaseModel


class TopicRelevancePresetBase(BaseModel):
    name: str
    description: Optional[str] = None
    preset_schema_version: int = 1
    preset_payload: Dict


class TopicRelevancePresetCreate(TopicRelevancePresetBase):
    pass


class TopicRelevancePresetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    preset_schema_version: Optional[int] = None
    preset_payload: Optional[Dict] = None
    is_active: Optional[bool] = None


class TopicRelevancePresetResponse(TopicRelevancePresetBase):
    id: UUID
    organization_id: int
    project_id: int
    is_active: bool
