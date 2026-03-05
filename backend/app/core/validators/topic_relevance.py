from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Callable, Dict, Optional

from guardrails.hub import LLMCritic
from guardrails import OnFailAction
from guardrails.validators import (
    Validator,
    register_validator,
    ValidationResult,
)
from guardrails.validators import PassResult, FailResult


def _build_topic_configuration(topic_config: Dict[str, str]) -> str:
    return "\n".join(
        f"- {topic}: {description}" for topic, description in topic_config.items()
    )


# This should be present in all prompt templates to indicate where the topic configuration will be inserted
_PROMPT_PLACEHOLDER = "{{TOPIC_CONFIGURATION}}"
_PROMPTS_DIR = Path(__file__).parent / "prompts" / "topic_relevance"


@lru_cache(maxsize=8)
def _load_prompt_template(prompt_version: int) -> str:
    if prompt_version < 1:
        raise ValueError("prompt_version must be a positive integer")

    prompt_file = _PROMPTS_DIR / f"v{prompt_version}.md"
    if not prompt_file.exists():
        raise ValueError(
            f"Topic relevance prompt template for version {prompt_version} not found"
        )

    template = prompt_file.read_text(encoding="utf-8")
    if _PROMPT_PLACEHOLDER not in template:
        raise ValueError(
            f"Prompt template v{prompt_version} must contain {_PROMPT_PLACEHOLDER}"
        )
    return template


def _build_metric_prompt(prompt_version: int, topic_config: Dict[str, str]) -> str:
    scope_text = _build_topic_configuration(topic_config)
    prompt_template = _load_prompt_template(prompt_version)
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
        topic_config: Dict[str, str],
        prompt_version: int = 1,
        llm_callable: str = "gpt-4o-mini",
        on_fail: Optional[Callable] = OnFailAction.EXCEPTION,
    ):
        super().__init__(on_fail=on_fail)

        if not topic_config:
            raise ValueError("topic_config cannot be empty")

        self.topic_config = topic_config
        self.prompt_version = prompt_version
        self.llm_callable = llm_callable

        self._critic = LLMCritic(
            metrics={
                "scope_violation": _build_metric_prompt(
                    prompt_version=prompt_version,
                    topic_config=topic_config,
                )
            },
            max_score=0,  # Only score 0 passes
            llm_callable=llm_callable,
            on_fail=on_fail,
        )

    def _validate(self, value: str, metadata: dict = None) -> ValidationResult:
        if not value or not value.strip():
            return FailResult(error_message="Empty message.")

        result = self._critic.validate(value, metadata=metadata)

        if result.passed:
            return PassResult(value=value)

        return FailResult(error_message="Message is outside the allowed topic scope.")
