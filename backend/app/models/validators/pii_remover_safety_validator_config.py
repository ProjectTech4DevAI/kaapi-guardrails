from __future__ import annotations
from typing import List, Literal, Optional

from app.models.base_validator_config import BaseValidatorConfig
from app.core.validators.pii_remover import PIIRemover

class PIIRemoverSafetyValidatorConfig(BaseValidatorConfig):
    type: Literal["pii_remover"]
    entity_types: Optional[List[str]] = None # list of PII entity types to remove
    threshold: float = 0.5 # confidence threshold for PII detection

    def build(self, *, on_fail):
        return PIIRemover(
            entity_types=self.entity_types,
            threshold=self.threshold,
            on_fail=on_fail,
        )
