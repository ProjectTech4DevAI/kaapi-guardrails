from guardrails import OnFailAction
from sqlmodel import SQLModel
from typing import Any, Callable, ClassVar, Optional, Type

class BaseValidatorConfig(SQLModel):
    on_fail: Optional[Callable] = OnFailAction.FIX

    model_config = {"arbitrary_types_allowed": True}

    def build(self) -> Any:
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement build()"
        )