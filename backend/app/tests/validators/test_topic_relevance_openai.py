from unittest.mock import MagicMock, patch

import pytest
from guardrails.validators import FailResult, PassResult

from app.core.validators.topic_relevance_openai import TopicRelevanceOpenAI

TOPIC_CONFIG = "Only answer questions about cooking and recipes."


def _make_llm_response(json_text: str) -> MagicMock:
    choice = MagicMock()
    choice.message.content = json_text
    result = MagicMock()
    result.choices = [choice]
    return result


@pytest.fixture
def validator():
    with patch(
        "app.core.validators.llm_utils.get_supported_openai_params",
        return_value=["response_format"],
    ):
        return TopicRelevanceOpenAI(system_prompt=TOPIC_CONFIG)


# ---------------------------------------------------------------------------
# PassResult — score >= threshold (2)
# ---------------------------------------------------------------------------


def test_passes_when_score_is_3(validator):
    with patch("app.core.validators.topic_relevance_openai.completion") as mock_llm:
        mock_llm.return_value = _make_llm_response('{"scope_violation": 3}')
        result = validator._validate("How do I make pasta?")

    assert isinstance(result, PassResult)
    assert result.metadata["scope_score"] == 3


def test_passes_when_score_equals_threshold(validator):
    with patch("app.core.validators.topic_relevance_openai.completion") as mock_llm:
        mock_llm.return_value = _make_llm_response('{"scope_violation": 2}')
        result = validator._validate("What is cooking roughly about?")

    assert isinstance(result, PassResult)
    assert result.metadata["scope_score"] == 2


# ---------------------------------------------------------------------------
# FailResult — score < threshold (1)
# ---------------------------------------------------------------------------


def test_fails_when_score_is_1(validator):
    with patch("app.core.validators.topic_relevance_openai.completion") as mock_llm:
        mock_llm.return_value = _make_llm_response('{"scope_violation": 1}')
        result = validator._validate("What is the latest cricket score?")

    assert isinstance(result, FailResult)
    assert "outside the allowed topic scope" in result.error_message
    assert result.metadata["scope_score"] == 1


# ---------------------------------------------------------------------------
# Custom threshold
# ---------------------------------------------------------------------------


def test_custom_threshold_of_3_fails_on_score_2():
    with patch(
        "app.core.validators.llm_utils.get_supported_openai_params",
        return_value=[],
    ):
        v = TopicRelevanceOpenAI(system_prompt=TOPIC_CONFIG, threshold=3)

    with patch("app.core.validators.topic_relevance_openai.completion") as mock_llm:
        mock_llm.return_value = _make_llm_response('{"scope_violation": 2}')
        result = v._validate("Something vaguely food related")

    assert isinstance(result, FailResult)
    assert result.metadata["scope_score"] == 2


def test_custom_threshold_of_1_passes_on_score_1():
    with patch(
        "app.core.validators.llm_utils.get_supported_openai_params",
        return_value=[],
    ):
        v = TopicRelevanceOpenAI(system_prompt=TOPIC_CONFIG, threshold=1)

    with patch("app.core.validators.topic_relevance_openai.completion") as mock_llm:
        mock_llm.return_value = _make_llm_response('{"scope_violation": 1}')
        result = v._validate("Cricket scores")

    assert isinstance(result, PassResult)


# ---------------------------------------------------------------------------
# Guard inputs
# ---------------------------------------------------------------------------


def test_fails_when_value_is_empty(validator):
    result = validator._validate("")

    assert isinstance(result, FailResult)
    assert "Empty message" in result.error_message


def test_fails_when_value_is_whitespace(validator):
    result = validator._validate("   ")

    assert isinstance(result, FailResult)
    assert "Empty message" in result.error_message


def test_fails_when_system_prompt_is_blank():
    with patch(
        "app.core.validators.llm_utils.get_supported_openai_params",
        return_value=[],
    ):
        v = TopicRelevanceOpenAI(system_prompt="")

    result = v._validate("Some input")

    assert isinstance(result, FailResult)
    assert "blank" in result.error_message


def test_fails_when_system_prompt_is_whitespace_only():
    with patch(
        "app.core.validators.llm_utils.get_supported_openai_params",
        return_value=[],
    ):
        v = TopicRelevanceOpenAI(system_prompt="   ")

    result = v._validate("Some input")

    assert isinstance(result, FailResult)
    assert "blank" in result.error_message


# ---------------------------------------------------------------------------
# LLM error handling
# ---------------------------------------------------------------------------


def test_fails_gracefully_when_llm_raises(validator):
    with patch(
        "app.core.validators.topic_relevance_openai.completion",
        side_effect=Exception("network timeout"),
    ):
        result = validator._validate("How do I bake bread?")

    assert isinstance(result, FailResult)
    assert "LLM call failed" in result.error_message
    assert "network timeout" in result.error_message


def test_fails_gracefully_when_response_is_not_json(validator):
    with patch("app.core.validators.topic_relevance_openai.completion") as mock_llm:
        mock_llm.return_value = _make_llm_response("Sure, this looks great!")
        result = validator._validate("How do I bake bread?")

    assert isinstance(result, FailResult)
    assert "unparseable" in result.error_message


def test_fails_gracefully_when_score_key_is_missing(validator):
    with patch("app.core.validators.topic_relevance_openai.completion") as mock_llm:
        mock_llm.return_value = _make_llm_response('{"result": "yes"}')
        result = validator._validate("How do I bake bread?")

    assert isinstance(result, FailResult)
    assert "unparseable" in result.error_message


def test_fails_gracefully_when_score_is_out_of_range(validator):
    with patch("app.core.validators.topic_relevance_openai.completion") as mock_llm:
        mock_llm.return_value = _make_llm_response('{"scope_violation": 5}')
        result = validator._validate("How do I bake bread?")

    assert isinstance(result, FailResult)
    assert "unparseable" in result.error_message


def test_fails_gracefully_when_score_is_a_string(validator):
    with patch("app.core.validators.topic_relevance_openai.completion") as mock_llm:
        mock_llm.return_value = _make_llm_response('{"scope_violation": "high"}')
        result = validator._validate("How do I bake bread?")

    assert isinstance(result, FailResult)
    assert "unparseable" in result.error_message


def test_passes_when_response_wrapped_in_markdown_fence(validator):
    with patch("app.core.validators.topic_relevance_openai.completion") as mock_llm:
        mock_llm.return_value = _make_llm_response(
            '```json\n{"scope_violation": 3}\n```'
        )
        result = validator._validate("How do I make pasta?")

    assert isinstance(result, PassResult)
    assert result.metadata["scope_score"] == 3


def test_passes_when_response_has_surrounding_prose(validator):
    with patch("app.core.validators.topic_relevance_openai.completion") as mock_llm:
        mock_llm.return_value = _make_llm_response(
            'Sure! Here is my evaluation: {"scope_violation": 2}'
        )
        result = validator._validate("Something vaguely food related")

    assert isinstance(result, PassResult)
    assert result.metadata["scope_score"] == 2


def test_fails_when_score_is_boolean(validator):
    with patch("app.core.validators.topic_relevance_openai.completion") as mock_llm:
        mock_llm.return_value = _make_llm_response('{"scope_violation": true}')
        result = validator._validate("How do I bake bread?")

    assert isinstance(result, FailResult)
    assert "unparseable" in result.error_message


# ---------------------------------------------------------------------------
# response_format forwarding
# ---------------------------------------------------------------------------


def test_response_format_passed_when_supported():
    with patch(
        "app.core.validators.llm_utils.get_supported_openai_params",
        return_value=["response_format"],
    ):
        v = TopicRelevanceOpenAI(system_prompt=TOPIC_CONFIG)

    with patch("app.core.validators.topic_relevance_openai.completion") as mock_llm:
        mock_llm.return_value = _make_llm_response('{"scope_violation": 3}')
        v._validate("How do I make pasta?")

    _, kwargs = mock_llm.call_args
    assert kwargs.get("response_format") == {"type": "json_object"}


def test_response_format_omitted_when_not_supported():
    with patch(
        "app.core.validators.llm_utils.get_supported_openai_params",
        return_value=[],
    ):
        v = TopicRelevanceOpenAI(system_prompt=TOPIC_CONFIG)

    with patch("app.core.validators.topic_relevance_openai.completion") as mock_llm:
        mock_llm.return_value = _make_llm_response('{"scope_violation": 3}')
        v._validate("How do I make pasta?")

    _, kwargs = mock_llm.call_args
    assert "response_format" not in kwargs


def test_response_format_omitted_when_litellm_check_fails():
    with patch(
        "app.core.validators.llm_utils.get_supported_openai_params",
        side_effect=Exception("litellm unavailable"),
    ):
        v = TopicRelevanceOpenAI(system_prompt=TOPIC_CONFIG)

    with patch("app.core.validators.topic_relevance_openai.completion") as mock_llm:
        mock_llm.return_value = _make_llm_response('{"scope_violation": 3}')
        v._validate("How do I make pasta?")

    _, kwargs = mock_llm.call_args
    assert "response_format" not in kwargs


# ---------------------------------------------------------------------------
# Prompt template content
# ---------------------------------------------------------------------------


def test_system_prompt_contains_topic_config():
    with patch(
        "app.core.validators.llm_utils.get_supported_openai_params",
        return_value=[],
    ):
        v = TopicRelevanceOpenAI(system_prompt=TOPIC_CONFIG)

    assert TOPIC_CONFIG in v._system_prompt


def test_system_prompt_contains_json_instruction():
    with patch(
        "app.core.validators.llm_utils.get_supported_openai_params",
        return_value=[],
    ):
        v = TopicRelevanceOpenAI(system_prompt=TOPIC_CONFIG)

    assert "scope_violation" in v._system_prompt
    assert "JSON" in v._system_prompt
