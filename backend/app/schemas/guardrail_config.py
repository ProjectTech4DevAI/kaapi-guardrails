from typing import Annotated, List, Optional, Union
from uuid import UUID

from pydantic import ConfigDict
from sqlmodel import Field, SQLModel

# todo this could be improved by having some auto-discovery mechanism inside
# validators. We'll not have to list every new validator like this.
from app.core.validators.config.ban_list_safety_validator_config import (
    BanListSafetyValidatorConfig,
)
from app.core.validators.config.gender_assumption_bias_safety_validator_config import (
    GenderAssumptionBiasSafetyValidatorConfig,
)
from app.core.validators.config.lexical_slur_safety_validator_config import (
    LexicalSlurSafetyValidatorConfig,
)
from app.core.validators.config.pii_remover_safety_validator_config import (
    PIIRemoverSafetyValidatorConfig,
)

ValidatorConfigItem = Annotated[
    # future validators will come here
    Union[
        BanListSafetyValidatorConfig,
        GenderAssumptionBiasSafetyValidatorConfig,
        LexicalSlurSafetyValidatorConfig,
        PIIRemoverSafetyValidatorConfig,
    ],
    Field(discriminator="type"),
]


class GuardrailRequest(SQLModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str
    input: str
    validators: List[ValidatorConfigItem]


class GuardrailResponse(SQLModel):
    response_id: UUID
    rephrase_needed: bool = False
    safe_text: Optional[str] = None
