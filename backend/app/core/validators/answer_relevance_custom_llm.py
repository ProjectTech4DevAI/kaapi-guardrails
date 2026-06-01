from __future__ import annotations

from collections.abc import Callable

from guardrails import OnFailAction
from guardrails.validators import (
    FailResult,
    PassResult,
    ValidationResult,
    Validator,
    register_validator,
)
from litellm import completion

from app.core.config import settings

DEFAULT_PROMPT_TEMPLATE = (
    "Query: {query}\n"
    "Answer: {answer}\n\n"
    "Does the answer fully satisfy the query and constraints?\n"
    "Answer only YES or NO."
)


@register_validator(name="answer-relevance-custom-llm", data_type="string")
class AnswerRelevanceCustomLLM(Validator):
    """
    Validates whether an LLM answer is relevant to the user query.

    Expects `value` to be the plain-text answer. The query must be provided
    via the `query` constructor argument (set by the validator config from
    payload.input before guard execution).
    Uses a configurable prompt template with {query} and {answer} placeholders.
    Returns PassResult for YES, FailResult for NO.
    """

    def __init__(
        self,
        prompt_template: str = DEFAULT_PROMPT_TEMPLATE,
        llm_callable: str = settings.ANSWER_RELEVANCE_LLM_MODEL,
        input: str = "",
        output: str = "",
        on_fail: Callable | None = OnFailAction.NOOP,
    ):
        super().__init__(on_fail=on_fail)
        self.prompt_template = prompt_template
        self.llm_callable = llm_callable
        self.input = input
        self.output = output

    def _validate(self, value: str, metadata: dict | None = None) -> ValidationResult:
        query = self.input
        answer = self.output

        if not query.strip() or not answer.strip():
            return FailResult(
                error_message="Both 'query' and 'answer' fields must be non-empty."
            )

        try:
            prompt = self.prompt_template.format(query=query, answer=answer)
        except KeyError as e:
            return FailResult(error_message=f"Prompt template missing placeholder: {e}")

        try:
            response = completion(
                model=self.llm_callable,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,
            )
            response_text = response.choices[0].message.content.strip().upper()
        except Exception as e:
            return FailResult(error_message=f"LLM call failed: {e}")

        if response_text.startswith("YES"):
            return PassResult(value=value)

        if response_text.startswith("NO"):
            return FailResult(
                error_message="The answer is not relevant to the query.",
            )

        return FailResult(
            error_message=f"Unexpected LLM response for relevance check: {response_text}"
        )
