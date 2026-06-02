from __future__ import annotations

import json
import re
from typing import Callable, Optional

from litellm import completion, get_supported_openai_params
from guardrails import OnFailAction
from guardrails.validators import (
    FailResult,
    PassResult,
    ValidationResult,
    Validator,
    register_validator,
)

from app.core.config import settings


_SCORING_INSTRUCTIONS = (
    "\n\nScore using:\n"
    "3 = clearly within scope (directly matches a topic description)\n"
    "2 = partially related (tangentially related or implicitly within scope)\n"
    "1 = clearly outside scope (no relation to any listed topic)\n"
    "\nRespond ONLY with a JSON object in this exact format: "
    '{"scope_violation": <score>} where <score> is the integer 1, 2, or 3.'
)


@register_validator(name="topic-relevance-openai", data_type="string")
class TopicRelevanceOpenAI(Validator):
    """
    Validates whether a user message is within the defined topic scope
    using a direct OpenAI/litellm call.

    The caller supplies the full system prompt. The validator appends
    hardcoded scoring and response-format instructions.

    Scores 1–3 where 3 = clearly in scope, 2 = ambiguous, 1 = outside scope.
    Passes when score >= threshold (default 2).
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

        try:
            self._supports_response_format = "response_format" in (
                get_supported_openai_params(model=llm_callable) or []
            )
        except Exception:
            self._supports_response_format = False

    def _validate(self, value: str, metadata: dict = None) -> ValidationResult:
        if self._invalid_config_reason:
            return FailResult(error_message=self._invalid_config_reason)

        if not value or not value.strip():
            return FailResult(error_message="Empty message.")

        try:
            kwargs = dict(
                model=self.llm_callable,
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": value},
                ],
                max_tokens=50,
            )
            if self._supports_response_format:
                kwargs["response_format"] = {"type": "json_object"}

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
            if type(score) is not int or score not in (1, 2, 3):
                raise ValueError(f"unexpected score value: {score!r}")
        except Exception as e:
            return FailResult(
                error_message=f"LLM returned an unparseable response: {e}. Raw: {content!r}"
            )

        if score >= self.threshold:
            return PassResult(value=value, metadata={"scope_score": score})

        return FailResult(
            error_message="Input is outside the allowed topic scope.",
            metadata={"scope_score": score},
        )
