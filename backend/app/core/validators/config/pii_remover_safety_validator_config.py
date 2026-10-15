from __future__ import annotations
from typing import List, Literal

from app.core.enum import PIIEntityType
from app.core.validators.pii_remover import DEFAULT_ENTITY_TYPES, PIIRemover
from app.core.validators.config.base_validator_config import BaseValidatorConfig


class PIIRemoverSafetyValidatorConfig(BaseValidatorConfig):
    # No use_enum_values here: it would also coerce the inherited on_fail to a
    # plain string, which resolve_on_fail() compares against GuardrailOnFail.
    type: Literal["pii_remover"]
    entity_types: List[PIIEntityType] = DEFAULT_ENTITY_TYPES

    def build(self):
        return PIIRemover(
            entity_types=[PIIEntityType(e).value for e in self.entity_types],
            on_fail=self.resolve_on_fail(),
        )
