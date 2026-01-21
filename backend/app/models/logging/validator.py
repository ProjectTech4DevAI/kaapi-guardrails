from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field

from app.utils import now

class ValidatorOutcome(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"

class ValidatorLog(SQLModel, table=True):
    __tablename__ = "validator_log"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    request_id: UUID = Field(foreign_key="request_log.id", nullable=False)
    name: str = Field(nullable=False)
    input: str = Field(nullable=False)
    output: str = Field(default="", nullable=False)
    error: str = Field(default="", nullable=False)
    outcome: ValidatorOutcome = Field(nullable=False)
    inserted_at: datetime = Field(default_factory=now, nullable=False)
    updated_at: datetime = Field(default_factory=now, nullable=False)
