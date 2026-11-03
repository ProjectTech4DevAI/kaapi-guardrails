from collections.abc import Callable

from guardrails import OnFailAction
from guardrails.validators import (
    FailResult,
    PassResult,
    ValidationResult,
    Validator,
    register_validator,
)

from app.core.enum import SlurSeverity
from app.core.validators.lexical_slur import LexicalSlur

TOXICITY_ERROR_MESSAGE = "Toxic content detected"
# Multilingual BERT fine-tuned on textdetox/multilingual_toxicity_dataset (HASOC,
# CONSTRAINT, TRAC-1 for hi/hinglish). F1 0.81 alone, 0.85 after the slur list on our
# 1,801-row Hindi/Hinglish/English benchmark. See issue #181.
DEFAULT_MODEL_NAME = "textdetox/bert-multilingual-toxicity-classifier"
DEFAULT_TOXIC_LABEL = "LABEL_1"
DEFAULT_TOXICITY_THRESHOLD = 0.5

_PIPELINE_CACHE: dict = {}


def _load_pipeline(model_name: str):
    if model_name not in _PIPELINE_CACHE:
        from transformers import pipeline as hf_pipeline

        _PIPELINE_CACHE[model_name] = hf_pipeline(
            "text-classification", model=model_name, top_k=None
        )
    return _PIPELINE_CACHE[model_name]


@register_validator(name="content-safety", data_type="string")
class ContentSafety(Validator):
    """
    Runs lexical slur redaction followed by a sentence-level toxicity classifier.

    Both checks run on the original text. The slur list gives spans, so a message
    whose only problem is a listed slur keeps its redacted form. The classifier
    returns one score per message, not spans; at or above `threshold` the whole
    message is replaced by `fallback_message` (or blanked when none is configured).
    The classifier must see the original text: redacting a slur hides the signal
    ("tu chutiya hai bhag yahan se" scores 1.00, the redacted form 0.24).
    """

    def __init__(
        self,
        slur_severity: SlurSeverity = SlurSeverity.All,
        threshold: float = DEFAULT_TOXICITY_THRESHOLD,
        model_name: str = DEFAULT_MODEL_NAME,
        toxic_label: str = DEFAULT_TOXIC_LABEL,
        fallback_message: str | None = None,
        on_fail: Callable | OnFailAction | None = OnFailAction.FIX,
    ):
        # Inner on_fail is never invoked; only this wrapper's on_fail applies.
        self._slur = LexicalSlur(severity=slur_severity, on_fail=OnFailAction.NOOP)
        self.threshold = threshold
        self.model_name = model_name
        self.toxic_label = toxic_label
        self.fallback_message = fallback_message
        self._pipeline = _load_pipeline(model_name)
        super().__init__(
            on_fail=on_fail,
            slur_severity=slur_severity,
            threshold=threshold,
            model_name=model_name,
            toxic_label=toxic_label,
            fallback_message=fallback_message,
        )

    def _toxicity_score(self, text: str) -> float:
        scores = self._pipeline(text, truncation=True)
        if scores and isinstance(scores[0], list):
            scores = scores[0]
        for item in scores:
            if item["label"] == self.toxic_label:
                return float(item["score"])
        raise ValueError(
            f"Model {self.model_name} emits labels "
            f"{[s['label'] for s in scores]}, expected toxic_label={self.toxic_label!r}"
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
        score = self._toxicity_score(value)
        if score >= self.threshold:
            errors.append(f"{TOXICITY_ERROR_MESSAGE} (score {score:.2f})")
            current = self.fallback_message or ""

        if not errors:
            return PassResult()

        return FailResult(error_message="; ".join(errors), fix_value=current)
