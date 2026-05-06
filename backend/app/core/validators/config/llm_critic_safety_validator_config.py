from typing import Literal

from guardrails.hub import LLMCritic

from app.core.config import settings
from app.core.constants import LLM_CRITIC_ERROR_MESSAGE
from app.core.enum import GuardrailOnFail
from app.core.validators.config.base_validator_config import BaseValidatorConfig

LLM_CRITIC_REPHRASE_MESSAGE = (
    f"{LLM_CRITIC_ERROR_MESSAGE} Please rephrase without unsafe content."
)


class LLMCriticSafetyValidatorConfig(BaseValidatorConfig):
    type: Literal["llm_critic"]
    metrics: dict
    max_score: int
    llm_callable: str

    def resolve_on_fail(self):
        if self.on_fail == GuardrailOnFail.Rephrase:
            return lambda value, fail_result: LLM_CRITIC_REPHRASE_MESSAGE
        return super().resolve_on_fail()

    def build(self):
        if not settings.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY is not configured. "
                "LLM critic validation requires an OpenAI API key."
            )
        return LLMCritic(
            metrics=self.metrics,
            max_score=self.max_score,
            llm_callable=self.llm_callable,
            on_fail=self.resolve_on_fail(),
        )
