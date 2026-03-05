from typing import Dict, Literal, Optional
from uuid import UUID

from app.core.validators.topic_relevance import TopicRelevance
from app.core.validators.config.base_validator_config import BaseValidatorConfig


class TopicRelevanceSafetyValidatorConfig(BaseValidatorConfig):
    type: Literal["topic_relevance"]
    configuration: Optional[Dict[str, str]] = None
    prompt_version: Optional[int] = None
    llm_callable: str = "gpt-4o-mini"
    topic_relevance_config_id: Optional[UUID] = None

    def build(self):
        return TopicRelevance(
            topic_config=self.configuration or {},
            prompt_version=self.prompt_version or 1,
            llm_callable=self.llm_callable,
            on_fail=self.resolve_on_fail(),
        )
