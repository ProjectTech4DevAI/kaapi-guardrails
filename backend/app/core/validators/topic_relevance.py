from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Callable, Optional

from guardrails.hub import LLMCritic
from guardrails import OnFailAction
from guardrails.validators import (
    Validator,
    register_validator,
    ValidationResult,
)
from guardrails.validators import FailResult, PassResult


# This should be present in all prompt templates to indicate where the topic configuration will be inserted
_PROMPT_PLACEHOLDER = "{{TOPIC_CONFIGURATION}}"
_PROMPTS_DIR = Path(__file__).parent / "prompts" / "topic_relevance"


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


def _build_metric_prompt(prompt_schema_version: int, topic_config: str) -> str:
    scope_text = topic_config.strip()
    if not scope_text:
        raise ValueError("topic_config cannot be empty")
    prompt_template = _load_prompt_template(prompt_schema_version)
    return prompt_template.replace(_PROMPT_PLACEHOLDER, scope_text)


@register_validator(name="topic-relevance", data_type="string")
class TopicRelevance(Validator):
    """
    Validates whether a user message is within the defined topic scope
    using Guardrails Hub's LLMCritic validator.

    If the message is clearly within scope → PassResult
    If partially related or outside scope → FailResult
    """

    def __init__(
        self,
        topic_config: str,
        prompt_schema_version: int = 1,
        llm_callable: str = "gpt-4o-mini",
        on_fail: Optional[Callable] = OnFailAction.NOOP,
    ):
        super().__init__(on_fail=on_fail)

        if not topic_config or not topic_config.strip():
            raise ValueError("topic_config cannot be empty")

        self.topic_config = topic_config
        self.prompt_schema_version = prompt_schema_version
        self.llm_callable = llm_callable

        try:
            from litellm import get_supported_openai_params

            supports_response_format = "response_format" in (
                get_supported_openai_params(model=llm_callable) or []
            )
        except Exception:
            supports_response_format = False

        self._critic = LLMCritic(
            metrics={
                "scope_violation": {
                    "description": _build_metric_prompt(
                        prompt_schema_version=prompt_schema_version,
                        topic_config=topic_config,
                    ),
                    "threshold": 2,
                }
            },
            max_score=3,
            llm_callable=llm_callable,
            on_fail=on_fail,
            **(
                {"llm_kwargs": {"response_format": {"type": "json_object"}}}
                if supports_response_format
                else {}
            ),
        )

    def _validate(self, value: str, metadata: dict = None) -> ValidationResult:
        if not value or not value.strip():
            return FailResult(error_message="Empty message.")

        try:
            result = self._critic.validate(value, metadata)
            score = None

            if getattr(result, "metadata", None):
                score = result.metadata.get("scope_violation")

            if isinstance(result, PassResult):
                return PassResult(value=value, metadata={"scope_score": score})

            if isinstance(result, FailResult):
                return FailResult(
                    error_message="Input is outside the allowed topic scope.",
                    metadata={"scope_score": score},
                )

        except Exception as e:
            return FailResult(
                error_message=f"LLM critic returned an invalid response: {e}"
            )

        return FailResult(error_message="Topic relevance validation failed.")
