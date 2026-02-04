from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field as SQLField
from sqlmodel import SQLModel, Field

from app.core.enum import GuardrailOnFail, Stage, ValidatorType
from app.utils import now

class ValidatorConfig(SQLModel, table=True):
    __tablename__ = "validator_config"

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        sa_column_kwargs={"comment": "Unique identifier for the validator configuration"},
    )

    org_id: int = Field(
        index=True,
        sa_column_kwargs={"comment": "Identifier for the organization"},
    )

    project_id: Optional[int] = Field(
        default=None, 
        index=True,
        sa_column_kwargs={"comment": "Identifier for the project"},
    )

    type: ValidatorType = Field(
        nullable=False,
        sa_column_kwargs={"comment": "Type of the validator"},
    )

    stage: Stage = Field(
        nullable=False,
        sa_column_kwargs={"comment": "Stage at which the validator is applied"},
    )

    on_fail_action: GuardrailOnFail = Field(
        default=GuardrailOnFail.Fix,
        nullable=False,
        sa_column_kwargs={"comment": "Action to take when the validator fails"},
    )

    config: dict[str, Any] = SQLField(
        default_factory=dict,
        sa_column=Column(
            JSONB,
            nullable=False,
            comment="Configuration for the validator",
        ),
        description=(
            "Configuration for the validator"
        ),
    )

    is_enabled: bool = Field(
        default=True,
        sa_column_kwargs={"comment": "Indicates if the validator is enabled"},
    )

    created_at: datetime = Field(
        default_factory=now,
        nullable=False,
        sa_column_kwargs={"comment": "Timestamp when the validator config was inserted"},
    )

    updated_at: datetime = Field(
        default_factory=now, 
        nullable=False,
        sa_column_kwargs={"comment": "Timestamp when the validator config was last updated"},
    )
