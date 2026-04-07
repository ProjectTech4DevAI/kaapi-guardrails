from datetime import datetime
from typing import Optional

from pydantic import ConfigDict
from sqlmodel import SQLModel, Field

from app.core.enum import GuardrailOnFail, Stage, ValidatorType


class ValidatorBase(SQLModel):
    model_config = ConfigDict(extra="allow")

    name: str = Field(min_length=5, max_length=225)
    type: ValidatorType
    stage: Stage
    on_fail_action: GuardrailOnFail = GuardrailOnFail.Fix
    is_enabled: bool = True


class ValidatorCreate(ValidatorBase):
    pass


class ValidatorUpdate(SQLModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str]
    type: Optional[ValidatorType] = None
    stage: Optional[Stage] = None
    on_fail_action: Optional[GuardrailOnFail] = None
    is_enabled: Optional[bool] = None


class ValidatorResponse(ValidatorBase):
    pass
