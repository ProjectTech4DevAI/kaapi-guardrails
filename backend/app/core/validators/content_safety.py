from collections.abc import Callable

from guardrails import OnFailAction
from guardrails.validators import (
    FailResult,
    PassResult,
    ValidationResult,
    Validator,
    register_validator,
)
from guardrails_ai.profanity_free import ProfanityFree

from app.core.enum import SlurSeverity
from app.core.validators.lexical_slur import LexicalSlur

PROFANITY_ERROR_MESSAGE = "Text contains profanity"


@register_validator(name="content-safety", data_type="string")
class ContentSafety(Validator):
    """
    Runs lexical slur redaction followed by profanity detection as one validator.

    The slur check runs first so a redacted slur doesn't trip ProfanityFree, which
    has no partial fix and would otherwise blank the whole text.
    """

    def __init__(
        self,
        slur_severity: SlurSeverity = SlurSeverity.All,
        on_fail: Callable | OnFailAction | None = OnFailAction.FIX,
    ):
        # Inner on_fail is never invoked; only this wrapper's on_fail applies.
        self._slur = LexicalSlur(severity=slur_severity, on_fail=OnFailAction.NOOP)
        self._profanity = ProfanityFree(on_fail=OnFailAction.NOOP)
        super().__init__(on_fail=on_fail, slur_severity=slur_severity)

    def _validate(self, value: str, metadata: dict | None = None) -> ValidationResult:
        metadata = metadata or {}
        errors = []
        current = value

        slur_result = self._slur.validate(current, metadata)
        if isinstance(slur_result, FailResult):
            errors.append(slur_result.error_message)
            current = slur_result.fix_value

        # ProfanityFree's own error_message embeds the full text; use a fixed one.
        if isinstance(self._profanity.validate(current, metadata), FailResult):
            errors.append(PROFANITY_ERROR_MESSAGE)
            current = ""

        if not errors:
            return PassResult()

        return FailResult(error_message="; ".join(errors), fix_value=current)
