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

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        sa_column_kwargs={"comment": "Unique identifier for the validator log entry"},
    )

    request_id: UUID = Field(
        foreign_key="request_log.id", 
        nullable=False,
        sa_column_kwargs={"comment": "Foreign key to the associated request log entry"},
    )

    name: str = Field(
        nullable=False,
        sa_column_kwargs={"comment": "Name of the validator used"},
    )

    input: str = Field(
        nullable=False,
        sa_column_kwargs={"comment": "Input message for the validator to check"},
    )

    output: str | None = Field(
        nullable=True,
        sa_column_kwargs={"comment": "Output message post validation"},
    )

    error: str | None = Field(
        nullable=True,
        sa_column_kwargs={"comment": "Error message if the validator throws an exception"},
    )

    outcome: ValidatorOutcome = Field(
        nullable=False,
        sa_column_kwargs={"comment": "Validator outcome (whether the validation failed or passed)"},
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