from typing import Literal, Optional
from uuid import UUID

from pydantic import Field

from app.core.config import settings
from app.core.validators.config.base_validator_config import BaseValidatorConfig
from app.core.validators.topic_relevance_openai import TopicRelevanceOpenAI


class TopicRelevanceOpenAISafetyValidatorConfig(BaseValidatorConfig):
    type: Literal["topic_relevance_openai"]
    configuration: Optional[str] = None
    llm_callable: str = settings.DEFAULT_LLM_CALLABLE
    threshold: int = Field(
        default=settings.TOPIC_RELEVANCE_OPENAI_THRESHOLD, ge=1, le=3
    )
    topic_relevance_config_id: Optional[UUID] = None

    def build(self):
        if not settings.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY is not configured. "
                "Topic relevance (OpenAI) validation requires an OpenAI API key."
            )
        return TopicRelevanceOpenAI(
            system_prompt=self.configuration or "",
            llm_callable=self.llm_callable,
            threshold=self.threshold,
            on_fail=self.resolve_on_fail(),
        )
