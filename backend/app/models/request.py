from sqlmodel import SQLModel, Field
from uuid import UUID, uuid4
from enum import Enum

from app.core.util import now
from datetime import datetime

class RequestStatus(str, Enum):
    PROCESSING = "processing"
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"

class RequestLog(SQLModel, table=True):
    __tablename__ = "request_log"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    request_id: UUID 
    response_id: UUID = Field(nullable=True)
    status: RequestStatus = Field(default=RequestStatus.PROCESSING)
    request_text: str = Field(nullable=False)
    response_text: str = Field(nullable=True)
    inserted_at: datetime = Field(default_factory=now, nullable=False)
    updated_at: datetime = Field(default_factory=now, nullable=False)

class RequestLogUpdate(SQLModel):
    response_text: str
    response_id: UUID