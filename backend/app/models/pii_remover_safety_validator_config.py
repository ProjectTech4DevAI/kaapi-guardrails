from __future__ import annotations
from typing import List, Literal, Optional

from app.models.base_validator_config import BaseValidatorConfig
from app.core.validators.pii_remover import PIIRemover

class PIIRemoverSafetyValidatorConfig(BaseValidatorConfig):
    type: Literal["pii_remover"]
    entity_types: Optional[List[str]] = None
    threshold: float = 0.5
    language: str = "en"

    def build(self):
        return PIIRemover(
            entity_types=self.entity_types,
            threshold=self.threshold,
            language=self.language,
            on_fail=self.resolve_on_fail(),
        )
