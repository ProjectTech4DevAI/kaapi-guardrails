import logging
from datetime import datetime, timezone
from pydantic import BaseModel
from typing import Any, Dict, Generic, Optional, TypeVar

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

T = TypeVar("T")

def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class APIResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    @classmethod
    def success_response(
        cls, data: T, metadata: Optional[Dict[str, Any]] = None
    ) -> "APIResponse[T]":
        return cls(success=True, data=data, metadata=metadata)

    @classmethod
    def failure_response(
        cls,
        error: str | list,
        data: Optional[T] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "APIResponse[T]":
        if isinstance(error, list):  # to handle cases when error is a list of errors
            error_message = "\n".join(
                [f"{err.get('loc', 'unknown')}: {err.get('msg', str(err))}" for err in error]
            )
        else:
            error_message = error

        return cls(success=False, data=data, error=error_message, metadata=metadata)
