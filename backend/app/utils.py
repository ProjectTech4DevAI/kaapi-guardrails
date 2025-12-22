import logging
from pydantic import BaseModel
from typing import Any, Dict, Generic, Optional, TypeVar

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

T = TypeVar("T")

class APIResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    @classmethod
    def success_response(
        cls, data: T, metadata: Optional[Dict[str, Any]] = None
    ) -> "APIResponse[T]":
        return cls(success=True, data=data, error=None, metadata=metadata)

    @classmethod
    def failure_response(
        cls,
        error: str | list,
        data: Optional[T] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "APIResponse[None]":
        if isinstance(error, list):  # to handle cases when error is a list of errors
            error_message = "\n".join(
                [f"{err.get('loc', 'unknown')}: {err.get('msg', str(err))}" for err in error]
            )
        else:
            error_message = error

        return cls(success=False, data=data, error=error_message, metadata=metadata)