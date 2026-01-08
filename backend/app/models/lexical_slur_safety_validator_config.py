from typing import List, Literal
from app.core.enum import SlurSeverity
from app.core.validators.lexical_slur import LexicalSlur
from app.models.base_validator_config import BaseValidatorConfig

class LexicalSlurSafetyValidatorConfig(BaseValidatorConfig):
    type: Literal["uli_slur_match"]
    languages: List[str] = ["en", "hi"]
    severity: Literal["low", "medium", "high", "all"] = "all"

    def build(self):
        return LexicalSlur(
            languages=self.languages,
            severity=SlurSeverity(self.severity),
            on_fail=self.resolve_on_fail(),
        )
