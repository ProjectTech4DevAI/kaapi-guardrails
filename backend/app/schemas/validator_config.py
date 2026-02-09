from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import SQLModel

from app.core.enum import GuardrailOnFail, Stage, ValidatorType


class ValidatorBase(SQLModel):
    model_config = {"extra": "allow"}
    id: UUID
    organization_id: int
    project_id: int
    type: ValidatorType
    stage: Stage
    on_fail_action: GuardrailOnFail
    is_enabled: bool = True
    created_at: datetime
    updated_at: datetime


class ValidatorCreate(ValidatorBase):
    pass


class ValidatorUpdate(SQLModel):
    # also allow extras for partial updates
    model_config = {"extra": "allow"}

    type: Optional[ValidatorType] = None
    stage: Optional[Stage] = None
    on_fail_action: Optional[GuardrailOnFail] = None
    is_enabled: Optional[bool] = None


class ValidatorResponse(ValidatorBase):
    pass
