from sqlmodel import Field, SQLModel
from typing import List, Union, Annotated

# todo this could be improved by having some auto-discovery mechanism inside
# validators. We'll not have to list every new validator like this.
from app.models.ban_list_safety_validator_config import BanListSafetyValidatorConfig
from app.models.gender_assumption_bias_safety_validator_config import GenderAssumptionBiasSafetyValidatorConfig
from app.models.lexical_slur_safety_validator_config import LexicalSlurSafetyValidatorConfig 
from app.models.pii_remover_safety_validator_config import PIIRemoverSafetyValidatorConfig

ValidatorConfigItem = Annotated[
    # future validators
    Union[
        BanListSafetyValidatorConfig,
        GenderAssumptionBiasSafetyValidatorConfig,
        LexicalSlurSafetyValidatorConfig, 
        PIIRemoverSafetyValidatorConfig
    ],
    Field(discriminator="type")
]

class GuardrailInputRequest(SQLModel):
    input: str
    validators: List[ValidatorConfigItem]

class GuardrailOutputRequest(SQLModel):
    output: str
    validators: List[ValidatorConfigItem]