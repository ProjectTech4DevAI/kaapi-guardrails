from typing import Any, Optional

from guardrails import OnFailAction
from sqlmodel import SQLModel

from app.core.enum import GuardrailOnFail
from app.core.on_fail_actions import rephrase_query_on_fail


_ON_FAIL_MAP = {
    GuardrailOnFail.Fix: OnFailAction.FIX,
    GuardrailOnFail.Exception: OnFailAction.EXCEPTION,
    GuardrailOnFail.Rephrase: rephrase_query_on_fail,
}

class BaseValidatorConfig(SQLModel):
    on_fail: GuardrailOnFail = GuardrailOnFail.Fix

    model_config = {"arbitrary_types_allowed": True}

    def resolve_on_fail(self):
        return _ON_FAIL_MAP[self.on_fail]

    def build(self, *, on_fail) -> Any:
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement build()"
        )