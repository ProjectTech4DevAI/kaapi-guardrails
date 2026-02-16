from datetime import datetime
from typing import Optional

from pydantic import ConfigDict
from sqlmodel import SQLModel

from app.core.enum import GuardrailOnFail, Stage, ValidatorType


class ValidatorBase(SQLModel):
    model_config = ConfigDict(extra="allow")

    type: ValidatorType
    stage: Stage
    on_fail_action: GuardrailOnFail = GuardrailOnFail.Fix
    is_enabled: bool = True


class ValidatorCreate(ValidatorBase):
    pass


class ValidatorBatchCreate(SQLModel):
    validators: list[ValidatorCreate]


class ValidatorBatchFetchItem(SQLModel):
    validator_config_id: int


class ValidatorUpdate(SQLModel):
    model_config = ConfigDict(extra="forbid")

    type: Optional[ValidatorType] = None
    stage: Optional[Stage] = None
    on_fail_action: Optional[GuardrailOnFail] = None
    is_enabled: Optional[bool] = None


class ValidatorResponse(ValidatorBase):
    id: int
    created_at: datetime
    updated_at: datetime
