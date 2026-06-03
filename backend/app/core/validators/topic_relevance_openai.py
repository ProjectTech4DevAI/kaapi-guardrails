from __future__ import annotations

import json
import re
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

# Valid scope scores returned by the model; the highest means "clearly in scope".
_VALID_SCORES = (1, 2, 3)
# Cap the response: a single ``{"scope_violation": <score>}`` object is tiny.
_MAX_TOKENS = 50

_SCORING_INSTRUCTIONS = (
    "\n\nScore using:\n"
    f"{_VALID_SCORES[2]} = clearly within scope (directly matches a topic description)\n"
    f"{_VALID_SCORES[1]} = partially related (tangentially related or implicitly within scope)\n"
    f"{_VALID_SCORES[0]} = clearly outside scope (no relation to any listed topic)\n"
    "\nRespond ONLY with a JSON object in this exact format: "
    '{"scope_violation": <score>} where <score> is the integer '
    f"{_VALID_SCORES[0]}, {_VALID_SCORES[1]}, or {_VALID_SCORES[2]}."
)


@register_validator(name="topic-relevance-openai", data_type="string")
class TopicRelevanceOpenAI(Validator):
    """
    Validates whether a user message is within the defined topic scope
    using a direct OpenAI/litellm call.

    The caller supplies the full system prompt. The validator appends
    hardcoded scoring and response-format instructions.

    Scores 1–3 where 3 = clearly in scope, 2 = partially related,
    1 = outside scope. Passes when score >= threshold (default 2).
    """

    def __init__(
        self,
        system_prompt: str,
        llm_callable: str = settings.DEFAULT_LLM_CALLABLE,
        threshold: int = settings.TOPIC_RELEVANCE_OPENAI_THRESHOLD,
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

        self._system_prompt = system_prompt.strip() + _SCORING_INSTRUCTIONS
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
            text = re.sub(r"```(?:json)?\s*|\s*```", "", content).strip()
            match = re.search(r"\{[^{}]*\}", text)
            if not match:
                raise ValueError("no JSON object found in response")
            data = json.loads(match.group())
            score = data.get("scope_violation")
            # `type(score) is not int` (not isinstance) deliberately rejects bool,
            # which is an int subclass, so `true`/`false` are treated as invalid.
            if type(score) is not int or score not in _VALID_SCORES:
                raise ValueError(f"unexpected score value: {score!r}")
        except Exception as e:
            return FailResult(
                error_message=f"LLM returned an unparseable response: {e}. Raw: {content!r}"
            )

        if score >= self.threshold:
            return PassResult(value=value, metadata={"scope_score": score})

        return FailResult(
            error_message=TOPIC_OUT_OF_SCOPE_ERROR,
            metadata={"scope_score": score},
        )
