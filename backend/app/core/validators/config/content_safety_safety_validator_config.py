from typing import Literal

from pydantic import Field

from app.core.enum import SlurSeverity
from app.core.validators.config.base_validator_config import BaseValidatorConfig
from app.core.validators.content_safety import (
    DEFAULT_PROFANITY_THRESHOLD,
    ContentSafety,
)


class ContentSafetySafetyValidatorConfig(BaseValidatorConfig):
    type: Literal["content_safety"]
    slur_severity: Literal[
        "low", "medium", "high", "all"
    ] = "all"  # minimum slur severity to flag
    # Profanity probability at or above which the text fails and is blanked.
    profanity_threshold: float = Field(default=DEFAULT_PROFANITY_THRESHOLD, ge=0, le=1)

    def build(self):
        return ContentSafety(
            slur_severity=SlurSeverity(self.slur_severity),
            profanity_threshold=self.profanity_threshold,
            on_fail=self.resolve_on_fail(),
        )
