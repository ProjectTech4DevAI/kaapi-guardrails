from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
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


_PROMPT_PLACEHOLDER = "{{TOPIC_CONFIGURATION}}"
_PROMPTS_DIR = Path(__file__).parent / "prompts" / "topic_relevance"

_JSON_INSTRUCTION = (
    "\n\nRespond ONLY with a JSON object in this exact format: "
    '{"scope_violation": <score>} where <score> is the integer 1, 2, or 3.'
)


@lru_cache(maxsize=8)
def _load_prompt_template(prompt_schema_version: int) -> str:
    if prompt_schema_version < 1:
        raise ValueError("prompt_schema_version must be a positive integer")
    prompt_file = _PROMPTS_DIR / f"v{prompt_schema_version}.md"
    if not prompt_file.exists():
        raise ValueError(
            f"Topic relevance prompt template for version {prompt_schema_version} not found"
        )
    template = prompt_file.read_text(encoding="utf-8")
    if _PROMPT_PLACEHOLDER not in template:
        raise ValueError(
            f"Prompt template v{prompt_schema_version} must contain {_PROMPT_PLACEHOLDER}"
        )
    return template


def _build_system_prompt(prompt_schema_version: int, topic_config: str) -> str:
    scope_text = topic_config.strip()
    if not scope_text:
        raise ValueError("topic_config cannot be empty")
    template = _load_prompt_template(prompt_schema_version)
    return template.replace(_PROMPT_PLACEHOLDER, scope_text) + _JSON_INSTRUCTION


@register_validator(name="topic-relevance-openai", data_type="string")
class TopicRelevanceOpenAI(Validator):
    """
    Validates whether a user message is within the defined topic scope
    using a direct OpenAI/litellm call.

    Scores 1–3 where 3 = clearly in scope, 2 = ambiguous, 1 = outside scope.
    Passes when score >= threshold (default 2).
    """

    def __init__(
        self,
        topic_config: str,
        prompt_schema_version: int = 1,
        llm_callable: str = "gpt-4o-mini",
        threshold: int = 2,
        on_fail: Optional[Callable] = OnFailAction.NOOP,
    ):
        super().__init__(on_fail=on_fail)

        self.topic_config = topic_config
        self.prompt_schema_version = prompt_schema_version
        self.llm_callable = llm_callable
        self.threshold = threshold
        self._invalid_config_reason: Optional[str] = None
        self._system_prompt: Optional[str] = None
        self._supports_response_format: bool = False

        if not topic_config or not topic_config.strip():
            self._invalid_config_reason = "topic_config is blank or missing"
            return

        try:
            self._system_prompt = _build_system_prompt(
                prompt_schema_version, topic_config
            )
        except ValueError as e:
            self._invalid_config_reason = str(e)
            return

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
            data = json.loads(content)
            score = data.get("scope_violation")
            if not isinstance(score, int) or score not in (1, 2, 3):
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
