from pydantic import ConfigDict, model_validator
from sqlmodel import Field, SQLModel

from app.core.enum import GuardrailOnFail, Stage, ValidatorType


class ValidatorBase(SQLModel):
    model_config = ConfigDict(extra="allow")

    name: str = Field(min_length=5, max_length=225)
    type: ValidatorType
    stage: Stage
    on_fail_action: GuardrailOnFail = GuardrailOnFail.Fix
    is_enabled: bool = True


class ValidatorCreate(ValidatorBase):
    @model_validator(mode="before")
    @classmethod
    def reject_body_tenant(cls, data: object) -> object:
        """The tenant must come from the X-ORGANIZATION-ID / X-PROJECT-ID
        headers, never the request body. Reject body tenant fields loudly
        instead of crashing the create path or being silently swallowed."""
        if isinstance(data, dict):
            reserved = [k for k in ("organization_id", "project_id") if k in data]
            if reserved:
                raise ValueError(
                    "Tenant must be provided via the X-ORGANIZATION-ID and "
                    "X-PROJECT-ID headers, not the request body: " + ", ".join(reserved)
                )
        return data


class ValidatorUpdate(SQLModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    type: ValidatorType | None = None
    stage: Stage | None = None
    on_fail_action: GuardrailOnFail | None = None
    is_enabled: bool | None = None


class ValidatorResponse(ValidatorBase):
    pass
