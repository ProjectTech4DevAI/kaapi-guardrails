from typing import List, Literal

from app.core.enum import SlurSeverity
from app.core.validators.lexical_slur import LexicalSlur
from app.core.validators.config.base_validator_config import BaseValidatorConfig


class LexicalSlurSafetyValidatorConfig(BaseValidatorConfig):
    type: Literal["uli_slur_match"]
    languages: List[str] = ["en", "hi"]  # list of languages to check slurs in
    severity: Literal[
        "low", "medium", "high", "all"
    ] = "all"  # severity level of slurs to check

    def build(self):
        return LexicalSlur(
            languages=self.languages,
            severity=SlurSeverity(self.severity),
            on_fail=self.resolve_on_fail(),
        )
