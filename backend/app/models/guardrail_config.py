from typing import List, Union, Annotated

from sqlmodel import Field, SQLModel

# todo this could be improved by having some auto-discovery mechanism inside
# validators. We'll not have to list every new validator like this.
from app.models.validators.ban_list_safety_validator_config import BanListSafetyValidatorConfig
from app.models.validators.gender_assumption_bias_safety_validator_config import GenderAssumptionBiasSafetyValidatorConfig
from app.models.validators.lexical_slur_safety_validator_config import LexicalSlurSafetyValidatorConfig 
from app.models.validators.pii_remover_safety_validator_config import PIIRemoverSafetyValidatorConfig

ValidatorConfigItem = Annotated[
    # future validators will come here
    Union[
        BanListSafetyValidatorConfig,
        GenderAssumptionBiasSafetyValidatorConfig,
        LexicalSlurSafetyValidatorConfig, 
        PIIRemoverSafetyValidatorConfig
    ],
    Field(discriminator="type")
]

class GuardrailInputRequest(SQLModel):
    request_id: str
    input: str
    validators: List[ValidatorConfigItem]

class GuardrailOutputRequest(SQLModel):
    request_id: str
    output: str
    validators: List[ValidatorConfigItem]