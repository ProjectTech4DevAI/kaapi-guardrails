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

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        sa_column_kwargs={"comment": "Unique identifier for the request log entry"},
    )

    request_id: UUID = Field(
        nullable=False,
        sa_column_kwargs={"comment": "Identifier for the request"},
    )

    response_id: Optional[UUID] = Field(
        default=None,
        nullable=True,
        sa_column_kwargs={"comment": "Identifier for the response"},
    )

    status: RequestStatus = Field(
        default=RequestStatus.PROCESSING,
        sa_column_kwargs={"comment": "Status of the request processing"},
    )

    request_text: str = Field(
        nullable=False,
        sa_column_kwargs={"comment": "Text of the request made"},
    )

    response_text: Optional[str] = Field(
        default=None,
        nullable=True,
        sa_column_kwargs={"comment": "Text of the response received"},
    )

    inserted_at: datetime = Field(
        default_factory=now,
        nullable=False,
        sa_column_kwargs={"comment": "Timestamp when the entry was created"},
    )

    updated_at: datetime = Field(
        default_factory=now,
        nullable=False,
        sa_column_kwargs={"comment": "Timestamp when the entry was last updated"},
    )


class RequestLogUpdate(SQLModel):
    response_text: str
    response_id: UUID
