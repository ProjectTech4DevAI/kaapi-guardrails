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

    # unique id of the validator log entry
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # request id (to be associated with request_log table)
    request_id: UUID = Field(foreign_key="request_log.id", nullable=False)

    # name of the validator
    name: str = Field(nullable=False)

    # input message for the validator to check
    input: str = Field(nullable=False)

    # output message post validation
    output: str | None = Field(nullable=True)

    # error, if any when the validator throws an exception
    error: str | None = Field(nullable=True)

    # validator outcome (whether the validation failed or passed)
    outcome: ValidatorOutcome = Field(nullable=False)

    # timestamp when the entry was inserted
    inserted_at: datetime = Field(default_factory=now, nullable=False)

    # timestamp when the entry was updated
    updated_at: datetime = Field(default_factory=now, nullable=False)