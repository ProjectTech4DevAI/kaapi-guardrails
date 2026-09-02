from __future__ import annotations
from typing import List, Literal, Optional

from app.core.validators.pii_remover import PIIRemover
from app.core.validators.config.base_validator_config import BaseValidatorConfig


class PIIRemoverSafetyValidatorConfig(BaseValidatorConfig):
    type: Literal["pii_remover"]
    entity_types: Optional[List[str]] = None
    threshold: Optional[float] = None
    nlp_engine_type: str = "spacy"
    model_name: Optional[str] = None

    def build(self):
        return PIIRemover(
            entity_types=self.entity_types,
            threshold=self.threshold,
            nlp_engine_type=self.nlp_engine_type,
            model_name=self.model_name,
            on_fail=self.resolve_on_fail(),
        )
