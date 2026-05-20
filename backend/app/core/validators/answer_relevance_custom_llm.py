from __future__ import annotations

import json
from typing import Callable, Optional

from litellm import completion
from guardrails import OnFailAction
from guardrails.validators import (
    FailResult,
    PassResult,
    ValidationResult,
    Validator,
    register_validator,
)

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

    Expects `value` to be a JSON string: {"query": "...", "answer": "..."}.
    Uses a configurable prompt template with {query} and {answer} placeholders.
    Returns PassResult for YES, FailResult for NO.
    """

    def __init__(
        self,
        prompt_template: str = DEFAULT_PROMPT_TEMPLATE,
        llm_callable: str = "gpt-4o-mini",
        on_fail: Optional[Callable] = OnFailAction.NOOP,
    ):
        super().__init__(on_fail=on_fail)
        self.prompt_template = prompt_template
        self.llm_callable = llm_callable

    def _validate(self, value: str, metadata: dict | None = None) -> ValidationResult:
        try:
            data = json.loads(value)
            query = data.get("query", "")
            answer = data.get("answer", "")
        except (json.JSONDecodeError, TypeError):
            return FailResult(
                error_message="Input must be a JSON string with 'query' and 'answer' fields."
            )

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
