from typing import Literal, Optional
from uuid import UUID

from pydantic import Field

from app.core.config import settings
from app.core.enum import GuardrailOnFail
from app.core.validators.config.base_validator_config import BaseValidatorConfig
from app.core.validators.topic_relevance_llm import TopicRelevanceLLM


class TopicRelevanceLLMSafetyValidatorConfig(BaseValidatorConfig):
    type: Literal["topic_relevance_llm"]
    configuration: Optional[str] = None
    llm_callable: str = settings.DEFAULT_LLM_CALLABLE
    threshold: int = Field(default=settings.TOPIC_RELEVANCE_LLM_THRESHOLD, ge=1, le=3)
    prompt_schema_version: int = Field(default=2, ge=1)
    topic_relevance_config_id: Optional[UUID] = None
    fallback_message: Optional[str] = Field(default=None, min_length=1)

    def resolve_on_fail(self):
        if self.on_fail == GuardrailOnFail.Rephrase and self.fallback_message:

            def _reply(value, fail_result):
                localized = (fail_result.metadata or {}).get("localized_fallback")
                return (
                    localized.strip() if isinstance(localized, str) else ""
                ) or self.fallback_message

            return _reply
        return super().resolve_on_fail()

    def build(self):
        if not settings.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY is not configured. "
                "Topic relevance (LLM) validation requires an OpenAI API key."
            )
        return TopicRelevanceLLM(
            system_prompt=self.configuration or "",
            llm_callable=self.llm_callable,
            threshold=self.threshold,
            prompt_schema_version=self.prompt_schema_version,
            fallback_message=self.fallback_message,
            on_fail=self.resolve_on_fail(),
        )
