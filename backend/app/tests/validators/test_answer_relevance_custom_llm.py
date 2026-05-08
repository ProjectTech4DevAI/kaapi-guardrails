import json
from unittest.mock import MagicMock, patch

import pytest
from guardrails.validators import FailResult, PassResult

from app.core.validators.answer_relevance_custom_llm import (
    DEFAULT_PROMPT_TEMPLATE,
    AnswerRelevanceCustomLLM,
)

VALID_INPUT = json.dumps(
    {"query": "What causes fever?", "answer": "Infections cause fever."}
)
VALID_INPUT_YES = VALID_INPUT
VALID_INPUT_NO = json.dumps(
    {"query": "What causes fever?", "answer": "The sky is blue."}
)


def _make_llm_response(text: str):
    choice = MagicMock()
    choice.message.content = text
    result = MagicMock()
    result.choices = [choice]
    return result


@pytest.fixture
def validator():
    return AnswerRelevanceCustomLLM()


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
        result = validator._validate(VALID_INPUT_YES)

    assert isinstance(result, PassResult)


def test_passes_when_llm_returns_yes_lowercase(validator):
    with patch(
        "app.core.validators.answer_relevance_custom_llm.completion"
    ) as mock_llm:
        mock_llm.return_value = _make_llm_response("yes")
        result = validator._validate(VALID_INPUT_YES)

    assert isinstance(result, PassResult)


def test_passes_when_llm_returns_yes_with_trailing_text(validator):
    with patch(
        "app.core.validators.answer_relevance_custom_llm.completion"
    ) as mock_llm:
        mock_llm.return_value = _make_llm_response("YES.")
        result = validator._validate(VALID_INPUT_YES)

    assert isinstance(result, PassResult)


# ---------------------------------------------------------------------------
# FailResult on NO
# ---------------------------------------------------------------------------


def test_fails_when_llm_returns_no(validator):
    with patch(
        "app.core.validators.answer_relevance_custom_llm.completion"
    ) as mock_llm:
        mock_llm.return_value = _make_llm_response("NO")
        result = validator._validate(VALID_INPUT_NO)

    assert isinstance(result, FailResult)
    assert "not relevant" in result.error_message


def test_fails_when_llm_returns_no_lowercase(validator):
    with patch(
        "app.core.validators.answer_relevance_custom_llm.completion"
    ) as mock_llm:
        mock_llm.return_value = _make_llm_response("no")
        result = validator._validate(VALID_INPUT_NO)

    assert isinstance(result, FailResult)


# ---------------------------------------------------------------------------
# Input parsing errors
# ---------------------------------------------------------------------------


def test_fails_with_non_json_input(validator):
    result = validator._validate("this is not json")

    assert isinstance(result, FailResult)
    assert "JSON" in result.error_message


def test_fails_with_empty_query(validator):
    value = json.dumps({"query": "", "answer": "Some answer."})
    result = validator._validate(value)

    assert isinstance(result, FailResult)
    assert "non-empty" in result.error_message


def test_fails_with_whitespace_only_query(validator):
    value = json.dumps({"query": "   ", "answer": "Some answer."})
    result = validator._validate(value)

    assert isinstance(result, FailResult)


def test_fails_with_empty_answer(validator):
    value = json.dumps({"query": "What is fever?", "answer": ""})
    result = validator._validate(value)

    assert isinstance(result, FailResult)
    assert "non-empty" in result.error_message


def test_fails_with_missing_query_key(validator):
    value = json.dumps({"answer": "Some answer."})
    result = validator._validate(value)

    assert isinstance(result, FailResult)


def test_fails_with_missing_answer_key(validator):
    value = json.dumps({"query": "What is fever?"})
    result = validator._validate(value)

    assert isinstance(result, FailResult)


# ---------------------------------------------------------------------------
# Custom prompt template
# ---------------------------------------------------------------------------


def test_custom_prompt_template_is_used():
    custom_template = "Q: {query}\nA: {answer}\nRelevant? YES or NO."
    validator = AnswerRelevanceCustomLLM(prompt_template=custom_template)

    with patch(
        "app.core.validators.answer_relevance_custom_llm.completion"
    ) as mock_llm:
        mock_llm.return_value = _make_llm_response("YES")
        validator._validate(VALID_INPUT_YES)

        call_args = mock_llm.call_args
        prompt_sent = call_args.kwargs["messages"][0]["content"]

    assert "Q: What causes fever?" in prompt_sent
    assert "A: Infections cause fever." in prompt_sent


def test_custom_prompt_with_unknown_placeholder_returns_fail_result():
    # str.format() raises KeyError for *unknown* keys, not for missing {answer}/{query}.
    bad_template = "Query: {query} Answer: {answer} Extra: {unknown_field}"
    validator = AnswerRelevanceCustomLLM(prompt_template=bad_template)

    result = validator._validate(VALID_INPUT_YES)

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
        result = validator._validate(VALID_INPUT_YES)

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
        result = validator._validate(VALID_INPUT_YES)

    assert isinstance(result, FailResult)
    assert "Unexpected" in result.error_message


# ---------------------------------------------------------------------------
# llm_callable is forwarded
# ---------------------------------------------------------------------------


def test_llm_callable_is_forwarded():
    validator = AnswerRelevanceCustomLLM(llm_callable="gpt-4o")

    with patch(
        "app.core.validators.answer_relevance_custom_llm.completion"
    ) as mock_llm:
        mock_llm.return_value = _make_llm_response("YES")
        validator._validate(VALID_INPUT_YES)

        call_args = mock_llm.call_args
        assert call_args.kwargs["model"] == "gpt-4o"
