from guardrails import OnFailAction
from guardrails.validators import Validator
from pydantic import ConfigDict
from sqlmodel import SQLModel

from app.core.enum import GuardrailOnFail
from app.core.on_fail_actions import rephrase_query_on_fail


_ON_FAIL_MAP = {
    GuardrailOnFail.Fix: OnFailAction.FIX,
    GuardrailOnFail.Exception: OnFailAction.EXCEPTION,
    GuardrailOnFail.Rephrase: rephrase_query_on_fail,
}


class BaseValidatorConfig(SQLModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    on_fail: GuardrailOnFail = GuardrailOnFail.Fix

    def resolve_on_fail(self):
        try:
            return _ON_FAIL_MAP[self.on_fail]
        except KeyError as e:
            raise ValueError(
                f"Invalid on_fail value: {self.on_fail}. Error {e}. "
                "Expected one of: exception, fix, rephrase."
            )

    def build(self) -> Validator:
        raise NotImplementedError(f"{self.__class__.__name__} must implement build()")
