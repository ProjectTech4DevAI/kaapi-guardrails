from typing import Literal, Optional

from pydantic import Field

from app.core.constants import CONTENT_SAFETY_DEFAULT_FALLBACK_MESSAGE
from app.core.enum import GuardrailOnFail, SlurSeverity
from app.core.validators.config.base_validator_config import BaseValidatorConfig
from app.core.validators.content_safety import (
    DEFAULT_MODEL_NAME,
    DEFAULT_TOXIC_LABEL,
    DEFAULT_TOXICITY_THRESHOLD,
    TOXICITY_ERROR_MESSAGE,
    ContentSafety,
    localize_fallback,
)


class ContentSafetySafetyValidatorConfig(BaseValidatorConfig):
    type: Literal["content_safety"]
    slur_severity: Literal["low", "medium", "high", "all"] = "all"
    threshold: float = Field(default=DEFAULT_TOXICITY_THRESHOLD, ge=0, le=1)
    # Any HuggingFace text-classification model; toxic_label must be one it emits
    # (textdetox bert / MuRIL: "LABEL_1", textdetox xlmr-large: "toxic").
    model_name: str = DEFAULT_MODEL_NAME
    toxic_label: str = DEFAULT_TOXIC_LABEL
    # Translated into the query's language; null blanks the text instead.
    fallback_message: Optional[str] = Field(
        default=CONTENT_SAFETY_DEFAULT_FALLBACK_MESSAGE, min_length=1
    )

    def resolve_on_fail(self):
        if self.on_fail == GuardrailOnFail.Rephrase and self.fallback_message:
            return self._rephrase_with_fallback
        return super().resolve_on_fail()

    def _rephrase_with_fallback(self, value: str, fail_result) -> str:
        # Toxic hit: the validator already put the translated fallback in fix_value.
        if TOXICITY_ERROR_MESSAGE in (fail_result.error_message or ""):
            return fail_result.fix_value
        return localize_fallback(self.fallback_message, value)

    def build(self):
        return ContentSafety(
            slur_severity=SlurSeverity(self.slur_severity),
            threshold=self.threshold,
            model_name=self.model_name,
            toxic_label=self.toxic_label,
            fallback_message=self.fallback_message,
            on_fail=self.resolve_on_fail(),
        )
