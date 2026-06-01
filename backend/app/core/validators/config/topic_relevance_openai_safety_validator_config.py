from typing import Literal, Optional
from uuid import UUID

from app.core.validators.topic_relevance_openai import TopicRelevanceOpenAI
from app.core.validators.config.base_validator_config import BaseValidatorConfig
from app.core.config import settings


class TopicRelevanceOpenAISafetyValidatorConfig(BaseValidatorConfig):
    type: Literal["topic_relevance_openai"]
    configuration: Optional[str] = None
    prompt_schema_version: Optional[int] = None
    llm_callable: str = "gpt-4o-mini"
    threshold: int = 2
    topic_relevance_config_id: Optional[UUID] = None

    def build(self):
        if not settings.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY is not configured. "
                "Topic relevance (OpenAI) validation requires an OpenAI API key."
            )
        return TopicRelevanceOpenAI(
            topic_config=self.configuration or " ",
            prompt_schema_version=self.prompt_schema_version or 1,
            llm_callable=self.llm_callable,
            threshold=self.threshold,
            on_fail=self.resolve_on_fail(),
        )
