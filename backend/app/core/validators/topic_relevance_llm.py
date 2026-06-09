from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Callable, Optional

from guardrails import OnFailAction
from guardrails.validators import (
    FailResult,
    PassResult,
    ValidationResult,
    Validator,
    register_validator,
)
from litellm import completion

from app.core.config import settings
from app.core.constants import EMPTY_MESSAGE_ERROR, TOPIC_OUT_OF_SCOPE_ERROR
from app.core.validators.llm_utils import (
    JSON_OBJECT_RESPONSE_FORMAT,
    supports_response_format,
)

_PROMPTS_DIR = Path(__file__).parent / "prompts" / "topic_relevance_llm"


def _extract_first_json_object(text: str) -> dict:
    """Find and parse the first complete JSON object in *text*."""
    start = text.find("{")
    if start == -1:
        raise ValueError("no JSON object found in response")
    obj, _ = json.JSONDecoder().raw_decode(text, start)
    return obj


# Valid scope scores returned by the model; the highest means "clearly in scope".
_VALID_SCORES = (1, 2, 3)
# Extra fields the model may return alongside scope_violation.
_OPTIONAL_FIELDS = (
    "interpreted_meaning",
    "reasoning",
    "classification_confidence_score",
)
# Budget for the richer 4-field JSON response.
_MAX_TOKENS = 300


@lru_cache(maxsize=8)
def _load_prompt_template(prompt_schema_version: int) -> str:
    """Load and cache the scoring instruction block for the given schema version."""
    if prompt_schema_version < 1:
        raise ValueError("prompt_schema_version must be a positive integer")

    prompt_file = _PROMPTS_DIR / f"v{prompt_schema_version}.md"
    if not prompt_file.exists():
        raise ValueError(
            f"Topic relevance (LLM) prompt template for version {prompt_schema_version} not found"
        )

    return prompt_file.read_text(encoding="utf-8")


@register_validator(name="topic-relevance-llm", data_type="string")
class TopicRelevanceLLM(Validator):
    """
    Validates whether a user message is within the defined topic scope
    using a direct LLM call via litellm.

    The caller supplies the topic configuration as ``system_prompt``. Scoring
    and response-format instructions are loaded from a versioned prompt template
    (v1/v2/v3) and appended to the system message. The user message contains
    only the raw query.

    Scores 1–3 where 3 = clearly in scope, 2 = partially related,
    1 = outside scope. Passes when score >= threshold (default 2).

    ``prompt_schema_version`` selects the scoring strategy:
      v1 = allowed topics only
      v2 = forbidden topics only
      v3 = combined allowed + forbidden (checks forbidden first)
    """

    def __init__(
        self,
        system_prompt: str,
        llm_callable: str = settings.DEFAULT_LLM_CALLABLE,
        threshold: int = settings.TOPIC_RELEVANCE_LLM_THRESHOLD,
        prompt_schema_version: int = 1,
        on_fail: Optional[Callable] = OnFailAction.NOOP,
    ):
        super().__init__(on_fail=on_fail)

        self.llm_callable = llm_callable
        self.threshold = threshold
        self._invalid_config_reason: Optional[str] = None
        self._system_prompt: Optional[str] = None
        self._supports_response_format: bool = False

        if not system_prompt or not system_prompt.strip():
            self._invalid_config_reason = "system_prompt is blank or missing"
            return

        try:
            scoring_rules = _load_prompt_template(prompt_schema_version)
        except ValueError as e:
            self._invalid_config_reason = str(e)
            return

        self._system_prompt = f"{system_prompt.strip()}\n\n{scoring_rules}"
        self._supports_response_format = supports_response_format(llm_callable)

    def _validate(
        self, value: str, metadata: Optional[dict] = None
    ) -> ValidationResult:
        if self._invalid_config_reason:
            return FailResult(error_message=self._invalid_config_reason)

        if not value or not value.strip():
            return FailResult(error_message=EMPTY_MESSAGE_ERROR)

        try:
            kwargs = {
                "model": self.llm_callable,
                "messages": [
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": value},
                ],
                "max_tokens": _MAX_TOKENS,
            }
            if self._supports_response_format:
                kwargs["response_format"] = JSON_OBJECT_RESPONSE_FORMAT

            response = completion(**kwargs)
            content = response.choices[0].message.content.strip()
        except Exception as e:
            return FailResult(error_message=f"LLM call failed: {e}")

        try:
            data = _extract_first_json_object(content)
            score = data.get("scope_violation")
            # `type(score) is not int` (not isinstance) deliberately rejects bool,
            # which is an int subclass, so `true`/`false` are treated as invalid.
            if type(score) is not int or score not in _VALID_SCORES:
                raise ValueError(f"unexpected score value: {score!r}")
        except Exception as e:
            return FailResult(
                error_message=f"LLM returned an unparseable response: {e}. Raw: {content!r}"
            )

        meta: dict = {"scope_score": score}
        for field in _OPTIONAL_FIELDS:
            if field in data:
                meta[field] = data[field]

        if score >= self.threshold:
            return PassResult(value=value, metadata=meta)

        return FailResult(
            error_message=TOPIC_OUT_OF_SCOPE_ERROR,
            metadata=meta,
        )
