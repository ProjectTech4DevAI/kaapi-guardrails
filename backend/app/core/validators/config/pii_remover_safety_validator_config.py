from __future__ import annotations
from typing import List, Literal

from pydantic import ConfigDict

from app.core.enum import PIIEntityType
from app.core.validators.pii_remover import DEFAULT_ENTITY_TYPES, PIIRemover
from app.core.validators.config.base_validator_config import BaseValidatorConfig


class PIIRemoverSafetyValidatorConfig(BaseValidatorConfig):
    model_config = ConfigDict(use_enum_values=True)

    type: Literal["pii_remover"]
    entity_types: List[PIIEntityType] = DEFAULT_ENTITY_TYPES

    def build(self):
        return PIIRemover(
            entity_types=self.entity_types,
            on_fail=self.resolve_on_fail(),
        )
