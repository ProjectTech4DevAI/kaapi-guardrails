from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field

from app.utils import now

class RequestStatus(str, Enum):
    PROCESSING = "processing"
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"


class RequestLog(SQLModel, table=True):
    __tablename__ = "request_log"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    request_id: UUID = Field(nullable=False)
    response_id: Optional[UUID] = Field(default=None, nullable=True)
    status: RequestStatus = Field(default=RequestStatus.PROCESSING)
    request_text: str = Field(nullable=False)
    response_text: Optional[str] = Field(default=None, nullable=True)
    inserted_at: datetime = Field(default_factory=now, nullable=False)
    updated_at: datetime = Field(default_factory=now, nullable=False)


class RequestLogUpdate(SQLModel):
    response_text: str
    response_id: UUID