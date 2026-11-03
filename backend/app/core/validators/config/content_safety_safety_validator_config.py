from typing import Literal, Optional

from pydantic import Field

from app.core.enum import GuardrailOnFail, SlurSeverity
from app.core.validators.config.base_validator_config import BaseValidatorConfig
from app.core.validators.content_safety import (
    DEFAULT_MODEL_NAME,
    DEFAULT_TOXIC_LABEL,
    DEFAULT_TOXICITY_THRESHOLD,
    ContentSafety,
)


class ContentSafetySafetyValidatorConfig(BaseValidatorConfig):
    type: Literal["content_safety"]
    slur_severity: Literal[
        "low", "medium", "high", "all"
    ] = "all"  # minimum slur severity to flag
    # Toxicity probability at or above which the whole message is replaced.
    threshold: float = Field(default=DEFAULT_TOXICITY_THRESHOLD, ge=0, le=1)
    # Any HuggingFace text-classification model; toxic_label must be one it emits
    # (textdetox bert / MuRIL: "LABEL_1", textdetox xlmr-large: "toxic").
    model_name: str = DEFAULT_MODEL_NAME
    toxic_label: str = DEFAULT_TOXIC_LABEL
    # Returned in place of a toxic message (fix) or as the rephrase reply.
    fallback_message: Optional[str] = Field(default=None, min_length=1)

    def resolve_on_fail(self):
        if self.on_fail == GuardrailOnFail.Rephrase and self.fallback_message:
            return lambda value, fail_result: self.fallback_message
        return super().resolve_on_fail()

    def build(self):
        return ContentSafety(
            slur_severity=SlurSeverity(self.slur_severity),
            threshold=self.threshold,
            model_name=self.model_name,
            toxic_label=self.toxic_label,
            fallback_message=self.fallback_message,
            on_fail=self.resolve_on_fail(),
        )
