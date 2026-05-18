from typing import Literal, Optional
from uuid import UUID

from app.core.config import settings
from app.core.validators.answer_relevance_custom_llm import AnswerRelevanceCustomLLM
from app.core.validators.config.base_validator_config import BaseValidatorConfig


class AnswerRelevanceCustomLLMSafetyValidatorConfig(BaseValidatorConfig):
    type: Literal["answer_relevance_custom_llm"]
    llm_callable: str = "gpt-4o-mini"
    # Inline prompt template with {query} and {answer} placeholders.
    # If None, the validator uses its built-in default.
    prompt_template: Optional[str] = None
    # Reference to a stored custom prompt; resolved to prompt_template before build().
    custom_prompt_id: Optional[UUID] = None

    def build(self):
        if not settings.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY is not configured. "
                "Answer relevance validation requires an OpenAI API key."
            )
        kwargs = dict(
            llm_callable=self.llm_callable,
            on_fail=self.resolve_on_fail(),
        )
        if self.prompt_template:
            kwargs["prompt_template"] = self.prompt_template
        return AnswerRelevanceCustomLLM(**kwargs)
