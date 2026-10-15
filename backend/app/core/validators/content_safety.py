from collections.abc import Callable

from guardrails import OnFailAction
from guardrails.validators import (
    FailResult,
    PassResult,
    ValidationResult,
    Validator,
    register_validator,
)
from profanity_check import predict_prob

from app.core.enum import SlurSeverity
from app.core.validators.lexical_slur import LexicalSlur

PROFANITY_ERROR_MESSAGE = "Text contains profanity"
# ProfanityFree uses the model's fixed 0.5 cutoff, which fails common Hinglish:
# the English model weights "ho" (as in "kaise ho") at 0.883 and "tu" at 0.535.
DEFAULT_PROFANITY_THRESHOLD = 0.9


@register_validator(name="content-safety", data_type="string")
class ContentSafety(Validator):
    """
    Runs lexical slur redaction followed by profanity detection as one validator.

    The slur check runs first so a redacted slur doesn't trip the profanity check,
    which has no partial fix and would otherwise blank the whole text. Profanity is
    scored with alt-profanity-check (the model behind ProfanityFree) against a
    configurable threshold instead of ProfanityFree's fixed 0.5.
    """

    def __init__(
        self,
        slur_severity: SlurSeverity = SlurSeverity.All,
        profanity_threshold: float = DEFAULT_PROFANITY_THRESHOLD,
        on_fail: Callable | OnFailAction | None = OnFailAction.FIX,
    ):
        # Inner on_fail is never invoked; only this wrapper's on_fail applies.
        self._slur = LexicalSlur(severity=slur_severity, on_fail=OnFailAction.NOOP)
        self.profanity_threshold = profanity_threshold
        super().__init__(
            on_fail=on_fail,
            slur_severity=slur_severity,
            profanity_threshold=profanity_threshold,
        )

    def _validate(self, value: str, metadata: dict | None = None) -> ValidationResult:
        metadata = metadata or {}
        errors = []
        current = value

        slur_result = self._slur.validate(current, metadata)
        if isinstance(slur_result, FailResult):
            errors.append(slur_result.error_message)
            current = slur_result.fix_value

        # Fixed message: never echo user text into logs or rephrase responses.
        if predict_prob([current])[0] >= self.profanity_threshold:
            errors.append(PROFANITY_ERROR_MESSAGE)
            current = ""

        if not errors:
            return PassResult()

        return FailResult(error_message="; ".join(errors), fix_value=current)
