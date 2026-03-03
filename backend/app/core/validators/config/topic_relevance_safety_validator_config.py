from __future__ import annotations
from typing import Dict, Literal

from app.core.validators.topic_relevance import TopicRelevanceValidator
from app.core.validators.config.base_validator_config import BaseValidatorConfig


class TopicRelevanceSafetyValidatorConfig(BaseValidatorConfig):
    type: Literal["topic_relevance"]
    scope_definitions: Dict[str, str]
    llm_callable: str

    def build(self):
        return TopicRelevanceValidator(
            scope_definitions=self.scope_definitions,
            llm_callable=self.llm_callable,
            on_fail=self.resolve_on_fail(),
        )
