from typing import Annotated, List, Optional, Union
from uuid import UUID

from pydantic import ConfigDict, model_validator
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

    @model_validator(mode="before")
    @classmethod
    def normalize_validators_from_config_api(cls, data):
        """
        Accept validator payloads coming from validator-config endpoints and
        map them into runtime validator-config shape expected by Guardrails.
        """
        if not isinstance(data, dict):
            return data

        validators = data.get("validators")
        if not isinstance(validators, list):
            return data

        normalized_payload = dict(data)
        normalized_validators = []

        drop_fields = {
            "id",
            "organization_id",
            "project_id",
            "stage",
            "is_enabled",
            "created_at",
            "updated_at",
        }

        for validator in validators:
            if not isinstance(validator, dict):
                normalized_validators.append(validator)
                continue

            normalized_validator = {
                key: value
                for key, value in validator.items()
                if key not in drop_fields and key != "on_fail_action"
            }

            if "on_fail" not in normalized_validator and "on_fail_action" in validator:
                normalized_validator["on_fail"] = validator["on_fail_action"]

            normalized_validators.append(normalized_validator)

        normalized_payload["validators"] = normalized_validators
        return normalized_payload


class GuardrailResponse(SQLModel):
    response_id: UUID
    rephrase_needed: bool = False
    safe_text: Optional[str] = None
