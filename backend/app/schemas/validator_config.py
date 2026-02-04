from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import SQLModel

from app.core.enum import GuardrailOnFail, Stage, ValidatorType


class ValidatorBase(SQLModel):
    model_config = {"extra": "allow"}

    type: ValidatorType
    stage: Stage
    on_fail_action: GuardrailOnFail
    is_enabled: bool = True


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
    id: UUID
    org_id: int
    project_id: Optional[int] = None
