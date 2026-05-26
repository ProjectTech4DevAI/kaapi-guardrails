from unittest.mock import MagicMock, patch

import pytest
from guardrails.validators import FailResult, PassResult

from app.core.validators.answer_relevance_custom_llm import (
    DEFAULT_PROMPT_TEMPLATE,
    AnswerRelevanceCustomLLM,
)

QUERY = "What causes fever?"
ANSWER_RELEVANT = "Infections cause fever."
ANSWER_IRRELEVANT = "The sky is blue."


def _make_llm_response(text: str):
    choice = MagicMock()
    choice.message.content = text
    result = MagicMock()
    result.choices = [choice]
    return result


@pytest.fixture
def validator():
    return AnswerRelevanceCustomLLM(input=QUERY, output=ANSWER_RELEVANT)


@pytest.fixture
def validator_irrelevant():
    return AnswerRelevanceCustomLLM(input=QUERY, output=ANSWER_IRRELEVANT)


# ---------------------------------------------------------------------------
# Default prompt template shape
# ---------------------------------------------------------------------------


def test_default_prompt_template_has_query_placeholder():
    assert "{query}" in DEFAULT_PROMPT_TEMPLATE


def test_default_prompt_template_has_answer_placeholder():
    assert "{answer}" in DEFAULT_PROMPT_TEMPLATE


# ---------------------------------------------------------------------------
# PassResult on YES
# ---------------------------------------------------------------------------


def test_passes_when_llm_returns_yes(validator):
    with patch(
        "app.core.validators.answer_relevance_custom_llm.completion"
    ) as mock_llm:
        mock_llm.return_value = _make_llm_response("YES")
        result = validator._validate(ANSWER_RELEVANT)

    assert isinstance(result, PassResult)


def test_passes_when_llm_returns_yes_lowercase(validator):
    with patch(
        "app.core.validators.answer_relevance_custom_llm.completion"
    ) as mock_llm:
        mock_llm.return_value = _make_llm_response("yes")
        result = validator._validate(ANSWER_RELEVANT)

    assert isinstance(result, PassResult)


def test_passes_when_llm_returns_yes_with_trailing_text(validator):
    with patch(
        "app.core.validators.answer_relevance_custom_llm.completion"
    ) as mock_llm:
        mock_llm.return_value = _make_llm_response("YES.")
        result = validator._validate(ANSWER_RELEVANT)

    assert isinstance(result, PassResult)


# ---------------------------------------------------------------------------
# FailResult on NO
# ---------------------------------------------------------------------------


def test_fails_when_llm_returns_no(validator_irrelevant):
    with patch(
        "app.core.validators.answer_relevance_custom_llm.completion"
    ) as mock_llm:
        mock_llm.return_value = _make_llm_response("NO")
        result = validator_irrelevant._validate(ANSWER_IRRELEVANT)

    assert isinstance(result, FailResult)
    assert "not relevant" in result.error_message


def test_fails_when_llm_returns_no_lowercase(validator_irrelevant):
    with patch(
        "app.core.validators.answer_relevance_custom_llm.completion"
    ) as mock_llm:
        mock_llm.return_value = _make_llm_response("no")
        result = validator_irrelevant._validate(ANSWER_IRRELEVANT)

    assert isinstance(result, FailResult)


# ---------------------------------------------------------------------------
# Empty / whitespace constructor params
# ---------------------------------------------------------------------------


def test_fails_with_empty_input():
    v = AnswerRelevanceCustomLLM(input="", output=ANSWER_RELEVANT)
    result = v._validate(ANSWER_RELEVANT)

    assert isinstance(result, FailResult)
    assert "non-empty" in result.error_message


def test_fails_with_whitespace_only_input():
    v = AnswerRelevanceCustomLLM(input="   ", output=ANSWER_RELEVANT)
    result = v._validate(ANSWER_RELEVANT)

    assert isinstance(result, FailResult)
    assert "non-empty" in result.error_message


def test_fails_with_empty_output():
    v = AnswerRelevanceCustomLLM(input=QUERY, output="")
    result = v._validate("")

    assert isinstance(result, FailResult)
    assert "non-empty" in result.error_message


def test_fails_with_whitespace_only_output():
    v = AnswerRelevanceCustomLLM(input=QUERY, output="   ")
    result = v._validate("   ")

    assert isinstance(result, FailResult)
    assert "non-empty" in result.error_message


# ---------------------------------------------------------------------------
# Custom prompt template
# ---------------------------------------------------------------------------


def test_custom_prompt_template_is_used():
    custom_template = "Q: {query}\nA: {answer}\nRelevant? YES or NO."
    v = AnswerRelevanceCustomLLM(
        prompt_template=custom_template,
        input=QUERY,
        output=ANSWER_RELEVANT,
    )

    with patch(
        "app.core.validators.answer_relevance_custom_llm.completion"
    ) as mock_llm:
        mock_llm.return_value = _make_llm_response("YES")
        v._validate(ANSWER_RELEVANT)

        prompt_sent = mock_llm.call_args.kwargs["messages"][0]["content"]

    assert f"Q: {QUERY}" in prompt_sent
    assert f"A: {ANSWER_RELEVANT}" in prompt_sent


def test_custom_prompt_with_unknown_placeholder_returns_fail_result():
    bad_template = "Query: {query} Answer: {answer} Extra: {unknown_field}"
    v = AnswerRelevanceCustomLLM(
        prompt_template=bad_template,
        input=QUERY,
        output=ANSWER_RELEVANT,
    )

    result = v._validate(ANSWER_RELEVANT)

    assert isinstance(result, FailResult)
    assert "placeholder" in result.error_message


# ---------------------------------------------------------------------------
# LLM call failure
# ---------------------------------------------------------------------------


def test_fails_when_llm_raises(validator):
    with patch(
        "app.core.validators.answer_relevance_custom_llm.completion"
    ) as mock_llm:
        mock_llm.side_effect = Exception("network error")
        result = validator._validate(ANSWER_RELEVANT)

    assert isinstance(result, FailResult)
    assert "LLM call failed" in result.error_message


# ---------------------------------------------------------------------------
# Unexpected LLM response
# ---------------------------------------------------------------------------


def test_fails_on_unexpected_llm_response(validator):
    with patch(
        "app.core.validators.answer_relevance_custom_llm.completion"
    ) as mock_llm:
        mock_llm.return_value = _make_llm_response("MAYBE")
        result = validator._validate(ANSWER_RELEVANT)

    assert isinstance(result, FailResult)
    assert "Unexpected" in result.error_message


# ---------------------------------------------------------------------------
# llm_callable is forwarded
# ---------------------------------------------------------------------------


def test_llm_callable_is_forwarded():
    v = AnswerRelevanceCustomLLM(
        llm_callable="gpt-4o",
        input=QUERY,
        output=ANSWER_RELEVANT,
    )

    with patch(
        "app.core.validators.answer_relevance_custom_llm.completion"
    ) as mock_llm:
        mock_llm.return_value = _make_llm_response("YES")
        v._validate(ANSWER_RELEVANT)

        assert mock_llm.call_args.kwargs["model"] == "gpt-4o"
