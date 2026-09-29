from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
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

    organization_id: int = Field(
        nullable=False,
        sa_column_kwargs={"comment": "Identifier for the organization"},
    )

    project_id: int = Field(
        nullable=False,
        sa_column_kwargs={"comment": "Identifier for the project"},
    )

    request_log_id: UUID = Field(
        foreign_key="request_log.id",
        nullable=False,
        sa_column_kwargs={"comment": "Foreign key to the associated request log entry"},
    )

    name: str = Field(
        nullable=False,
        sa_column_kwargs={"comment": "Name of the validator used"},
    )

    order: int | None = Field(
        default=None,
        nullable=True,
        sa_column_kwargs={
            "comment": "1-based execution order of the validator within the request"
        },
    )

    duration_ms: int | None = Field(
        default=None,
        nullable=True,
        sa_column_kwargs={
            "comment": "Wall-clock execution time of the validator in milliseconds"
        },
    )

    stage: str | None = Field(
        default=None,
        nullable=True,
        sa_column_kwargs={"comment": "Stage the validator checked (input or output)"},
    )

    type: str | None = Field(
        default=None,
        nullable=True,
        sa_column_kwargs={"comment": "Validator type (ValidatorType enum value)"},
    )

    meta: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(
            "metadata",
            JSONB,
            nullable=True,
            comment="Full resolved validator config used for this run",
        ),
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
        sa_column_kwargs={
            "comment": "Error message if the validator throws an exception"
        },
    )

    outcome: ValidatorOutcome = Field(
        nullable=False,
        sa_column_kwargs={
            "comment": "Validator outcome (whether the validation failed or passed)"
        },
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
