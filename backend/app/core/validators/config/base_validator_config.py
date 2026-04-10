from typing import Any, Dict, Optional

from guardrails import OnFailAction
from guardrails.validators import FailResult, Validator
from pydantic import ConfigDict
from sqlmodel import SQLModel

from app.core.enum import GuardrailOnFail
from app.core.on_fail_actions import rephrase_query_on_fail


class BaseValidatorConfig(SQLModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    on_fail: GuardrailOnFail = GuardrailOnFail.Fix
    validator_metadata: Optional[Dict[str, Any]] = None

    def _on_fix(self, value: str, fail_result: FailResult):
        fix_value = fail_result.fix_value if fail_result else None
        if not fix_value:
            self.validator_metadata = {
<<<<<<< feat/toxicity-huggingface-model
                "reason": f"Empty string has been returned since the validation failed for: {self.type}"
            }
=======
                "reason": f"Empty string has been returned since the validation failed for: {self.type}"  # type: ignore[attr-defined]
            }
            return ""
>>>>>>> feat/toxicity-hub-validators
        return fix_value

    def resolve_on_fail(self):
        if self.on_fail == GuardrailOnFail.Fix:
            return self._on_fix
        elif self.on_fail == GuardrailOnFail.Exception:
            return OnFailAction.EXCEPTION
        elif self.on_fail == GuardrailOnFail.Rephrase:
            return rephrase_query_on_fail
        raise ValueError(
            f"Invalid on_fail value: {self.on_fail}. "
            "Expected one of: exception, fix, rephrase."
        )

    def build(self) -> Validator:
        raise NotImplementedError(f"{self.__class__.__name__} must implement build()")
