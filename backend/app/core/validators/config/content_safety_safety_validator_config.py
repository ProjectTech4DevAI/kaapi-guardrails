from typing import Literal

from app.core.enum import SlurSeverity
from app.core.validators.config.base_validator_config import BaseValidatorConfig
from app.core.validators.content_safety import ContentSafety


class ContentSafetySafetyValidatorConfig(BaseValidatorConfig):
    type: Literal["content_safety"]
    slur_severity: Literal[
        "low", "medium", "high", "all"
    ] = "all"  # minimum slur severity to flag; profanity check has no knobs

    def build(self):
        return ContentSafety(
            slur_severity=SlurSeverity(self.slur_severity),
            on_fail=self.resolve_on_fail(),
        )
