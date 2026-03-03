from typing import Literal

from guardrails.hub import LLMCritic

from app.core.validators.config.base_validator_config import BaseValidatorConfig


class LLMCriticSafetyValidatorConfig(BaseValidatorConfig):
    type: Literal["llm_critic"]
    metrics: dict
    max_score: int
    llm_callable: str

    def build(self):
        return LLMCritic(
            metrics=self.metrics,
            max_score=self.max_score,
            llm_callable=self.llm_callable,
            on_fail=self.resolve_on_fail(),
        )
