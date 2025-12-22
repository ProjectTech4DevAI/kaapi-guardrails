from typing import Any, Optional
from pydantic import BaseModel

class APIResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[Any] = None
    metadata: Optional[Any] = None

    @classmethod
    def success_response(cls, data: Any, metadata: Any = None):
        return cls(success=True, data=data, metadata=metadata)

    @classmethod
    def failure_response(cls, error: Any, metadata: Any = None):
        return cls(success=False, error=error, metadata=metadata)