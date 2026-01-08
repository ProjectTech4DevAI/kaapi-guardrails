from guardrails import OnFailAction
from sqlmodel import SQLModel
from typing import Any, Literal, Optional

ON_FAIL_STR = Literal["exception", "fix", "noop", "reask"]

class BaseValidatorConfig(SQLModel):
    on_fail: Optional[ON_FAIL_STR] = OnFailAction.FIX

    model_config = {"arbitrary_types_allowed": True}

    def resolve_on_fail(self):
        if self.on_fail is None:
            return None

        try:
            return OnFailAction[self.on_fail.upper()]
        except KeyError:
            raise ValueError(
                f"Invalid on_fail value: {self.on_fail}. "
                "Expected one of: exception, fix, noop, reask"
            )            

    def build(self) -> Any:
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement build()"
        )