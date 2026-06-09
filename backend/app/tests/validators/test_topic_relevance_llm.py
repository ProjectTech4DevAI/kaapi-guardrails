from unittest.mock import MagicMock, patch

import pytest
from guardrails.validators import FailResult, PassResult

from app.core.validators.topic_relevance_llm import TopicRelevanceLLM

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
        return TopicRelevanceLLM(system_prompt=TOPIC_CONFIG)


# ---------------------------------------------------------------------------
# PassResult — score >= threshold (2)
# ---------------------------------------------------------------------------


def test_passes_when_score_is_3(validator):
    with patch("app.core.validators.topic_relevance_llm.completion") as mock_llm:
        mock_llm.return_value = _make_llm_response('{"scope_violation": 3}')
        result = validator._validate("How do I make pasta?")

    assert isinstance(result, PassResult)
    assert result.metadata["scope_score"] == 3


def test_passes_when_score_equals_threshold(validator):
    with patch("app.core.validators.topic_relevance_llm.completion") as mock_llm:
        mock_llm.return_value = _make_llm_response('{"scope_violation": 2}')
        result = validator._validate("What is cooking roughly about?")

    assert isinstance(result, PassResult)
    assert result.metadata["scope_score"] == 2


# ---------------------------------------------------------------------------
# FailResult — score < threshold (1)
# ---------------------------------------------------------------------------


def test_fails_when_score_is_1(validator):
    with patch("app.core.validators.topic_relevance_llm.completion") as mock_llm:
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
        strict_validator = TopicRelevanceLLM(system_prompt=TOPIC_CONFIG, threshold=3)

    with patch("app.core.validators.topic_relevance_llm.completion") as mock_llm:
        mock_llm.return_value = _make_llm_response('{"scope_violation": 2}')
        result = strict_validator._validate("Something vaguely food related")

    assert isinstance(result, FailResult)
    assert result.metadata["scope_score"] == 2


def test_custom_threshold_of_1_passes_on_score_1():
    with patch(
        "app.core.validators.llm_utils.get_supported_openai_params",
        return_value=[],
    ):
        lenient_validator = TopicRelevanceLLM(system_prompt=TOPIC_CONFIG, threshold=1)

    with patch("app.core.validators.topic_relevance_llm.completion") as mock_llm:
        mock_llm.return_value = _make_llm_response('{"scope_violation": 1}')
        result = lenient_validator._validate("Cricket scores")

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
        blank_prompt_validator = TopicRelevanceLLM(system_prompt="")

    result = blank_prompt_validator._validate("Some input")

    assert isinstance(result, FailResult)
    assert "blank" in result.error_message


def test_fails_when_system_prompt_is_whitespace_only():
    with patch(
        "app.core.validators.llm_utils.get_supported_openai_params",
        return_value=[],
    ):
        whitespace_prompt_validator = TopicRelevanceLLM(system_prompt="   ")

    result = whitespace_prompt_validator._validate("Some input")

    assert isinstance(result, FailResult)
    assert "blank" in result.error_message


# ---------------------------------------------------------------------------
# LLM error handling
# ---------------------------------------------------------------------------


def test_fails_gracefully_when_llm_raises(validator):
    with patch(
        "app.core.validators.topic_relevance_llm.completion",
        side_effect=Exception("network timeout"),
    ):
        result = validator._validate("How do I bake bread?")

    assert isinstance(result, FailResult)
    assert "LLM call failed" in result.error_message
    assert "network timeout" in result.error_message


def test_fails_gracefully_when_response_is_not_json(validator):
    with patch("app.core.validators.topic_relevance_llm.completion") as mock_llm:
        mock_llm.return_value = _make_llm_response("Sure, this looks great!")
        result = validator._validate("How do I bake bread?")

    assert isinstance(result, FailResult)
    assert "unparseable" in result.error_message


def test_fails_gracefully_when_score_key_is_missing(validator):
    with patch("app.core.validators.topic_relevance_llm.completion") as mock_llm:
        mock_llm.return_value = _make_llm_response('{"result": "yes"}')
        result = validator._validate("How do I bake bread?")

    assert isinstance(result, FailResult)
    assert "unparseable" in result.error_message


def test_fails_gracefully_when_score_is_out_of_range(validator):
    with patch("app.core.validators.topic_relevance_llm.completion") as mock_llm:
        mock_llm.return_value = _make_llm_response('{"scope_violation": 5}')
        result = validator._validate("How do I bake bread?")

    assert isinstance(result, FailResult)
    assert "unparseable" in result.error_message


def test_fails_gracefully_when_score_is_a_string(validator):
    with patch("app.core.validators.topic_relevance_llm.completion") as mock_llm:
        mock_llm.return_value = _make_llm_response('{"scope_violation": "high"}')
        result = validator._validate("How do I bake bread?")

    assert isinstance(result, FailResult)
    assert "unparseable" in result.error_message


def test_passes_when_response_wrapped_in_markdown_fence(validator):
    with patch("app.core.validators.topic_relevance_llm.completion") as mock_llm:
        mock_llm.return_value = _make_llm_response(
            '```json\n{"scope_violation": 3}\n```'
        )
        result = validator._validate("How do I make pasta?")

    assert isinstance(result, PassResult)
    assert result.metadata["scope_score"] == 3


def test_passes_when_response_wrapped_in_plain_markdown_fence(validator):
    with patch("app.core.validators.topic_relevance_llm.completion") as mock_llm:
        mock_llm.return_value = _make_llm_response('```\n{"scope_violation": 3}\n```')
        result = validator._validate("How do I make pasta?")

    assert isinstance(result, PassResult)
    assert result.metadata["scope_score"] == 3


def test_passes_when_response_has_surrounding_prose(validator):
    with patch("app.core.validators.topic_relevance_llm.completion") as mock_llm:
        mock_llm.return_value = _make_llm_response(
            'Sure! Here is my evaluation: {"scope_violation": 2}'
        )
        result = validator._validate("Something vaguely food related")

    assert isinstance(result, PassResult)
    assert result.metadata["scope_score"] == 2


# ---------------------------------------------------------------------------
# Richer 4-field response format
# ---------------------------------------------------------------------------

_RICH_PASS = (
    '{"interpreted_meaning": "How to cook pasta",'
    ' "reasoning": "Directly about cooking.",'
    ' "scope_violation": 3,'
    ' "classification_confidence_score": "high"}'
)

_RICH_FAIL = (
    '{"interpreted_meaning": "Latest cricket score",'
    ' "reasoning": "Unrelated to cooking.",'
    ' "scope_violation": 1,'
    ' "classification_confidence_score": "high"}'
)


def test_passes_with_rich_format_and_exposes_extra_metadata(validator):
    with patch("app.core.validators.topic_relevance_llm.completion") as mock_llm:
        mock_llm.return_value = _make_llm_response(_RICH_PASS)
        result = validator._validate("How do I make pasta?")

    assert isinstance(result, PassResult)
    assert result.metadata["scope_score"] == 3
    assert result.metadata["interpreted_meaning"] == "How to cook pasta"
    assert result.metadata["reasoning"] == "Directly about cooking."
    assert result.metadata["classification_confidence_score"] == "high"


def test_fails_with_rich_format_and_exposes_extra_metadata(validator):
    with patch("app.core.validators.topic_relevance_llm.completion") as mock_llm:
        mock_llm.return_value = _make_llm_response(_RICH_FAIL)
        result = validator._validate("What is the latest cricket score?")

    assert isinstance(result, FailResult)
    assert result.metadata["scope_score"] == 1
    assert result.metadata["interpreted_meaning"] == "Latest cricket score"
    assert result.metadata["reasoning"] == "Unrelated to cooking."
    assert result.metadata["classification_confidence_score"] == "high"


def test_passes_when_rich_format_wrapped_in_markdown_fence(validator):
    with patch("app.core.validators.topic_relevance_llm.completion") as mock_llm:
        mock_llm.return_value = _make_llm_response(f"```json\n{_RICH_PASS}\n```")
        result = validator._validate("How do I make pasta?")

    assert isinstance(result, PassResult)
    assert result.metadata["scope_score"] == 3


def test_reasoning_with_curly_braces_is_parsed_correctly(validator):
    response = (
        '{"interpreted_meaning": "A cooking query",'
        ' "reasoning": "Query {clearly} fits cooking scope.",'
        ' "scope_violation": 3,'
        ' "classification_confidence_score": "high"}'
    )
    with patch("app.core.validators.topic_relevance_llm.completion") as mock_llm:
        mock_llm.return_value = _make_llm_response(response)
        result = validator._validate("How do I make pasta?")

    assert isinstance(result, PassResult)
    assert result.metadata["scope_score"] == 3


def test_fails_when_score_is_boolean(validator):
    with patch("app.core.validators.topic_relevance_llm.completion") as mock_llm:
        mock_llm.return_value = _make_llm_response('{"scope_violation": true}')
        result = validator._validate("How do I bake bread?")

    assert isinstance(result, FailResult)
    assert "unparseable" in result.error_message


# ---------------------------------------------------------------------------
# User message construction
# ---------------------------------------------------------------------------


def test_user_message_is_exactly_the_query(validator):
    query = "How do I make pasta?"
    with patch("app.core.validators.topic_relevance_llm.completion") as mock_llm:
        mock_llm.return_value = _make_llm_response('{"scope_violation": 3}')
        validator._validate(query)

    _, kwargs = mock_llm.call_args
    user_message = kwargs["messages"][1]["content"]
    assert user_message == query


# ---------------------------------------------------------------------------
# response_format forwarding
# ---------------------------------------------------------------------------


def test_response_format_passed_when_supported():
    with patch(
        "app.core.validators.llm_utils.get_supported_openai_params",
        return_value=["response_format"],
    ):
        validator = TopicRelevanceLLM(system_prompt=TOPIC_CONFIG)

    with patch("app.core.validators.topic_relevance_llm.completion") as mock_llm:
        mock_llm.return_value = _make_llm_response('{"scope_violation": 3}')
        validator._validate("How do I make pasta?")

    _, kwargs = mock_llm.call_args
    assert kwargs.get("response_format") == {"type": "json_object"}


def test_response_format_omitted_when_not_supported():
    # Use an unknown model so the static allowlist doesn't short-circuit.
    with patch(
        "app.core.validators.llm_utils.get_supported_openai_params",
        return_value=[],
    ):
        validator = TopicRelevanceLLM(
            system_prompt=TOPIC_CONFIG, llm_callable="unknown-model"
        )

    with patch("app.core.validators.topic_relevance_llm.completion") as mock_llm:
        mock_llm.return_value = _make_llm_response('{"scope_violation": 3}')
        validator._validate("How do I make pasta?")

    _, kwargs = mock_llm.call_args
    assert "response_format" not in kwargs


def test_response_format_omitted_when_litellm_check_fails():
    # Use an unknown model so the static allowlist doesn't short-circuit.
    with patch(
        "app.core.validators.llm_utils.get_supported_openai_params",
        side_effect=Exception("litellm unavailable"),
    ):
        validator = TopicRelevanceLLM(
            system_prompt=TOPIC_CONFIG, llm_callable="unknown-model"
        )

    with patch("app.core.validators.topic_relevance_llm.completion") as mock_llm:
        mock_llm.return_value = _make_llm_response('{"scope_violation": 3}')
        validator._validate("How do I make pasta?")

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
        validator = TopicRelevanceLLM(system_prompt=TOPIC_CONFIG)

    assert TOPIC_CONFIG in validator._system_prompt


def test_system_prompt_contains_json_instruction():
    with patch(
        "app.core.validators.llm_utils.get_supported_openai_params",
        return_value=[],
    ):
        validator = TopicRelevanceLLM(system_prompt=TOPIC_CONFIG)

    assert "scope_violation" in validator._system_prompt
    assert "JSON" in validator._system_prompt


def test_prompt_schema_version_v2_loads_forbidden_template():
    with patch(
        "app.core.validators.llm_utils.get_supported_openai_params",
        return_value=[],
    ):
        v2_validator = TopicRelevanceLLM(
            system_prompt=TOPIC_CONFIG, prompt_schema_version=2
        )

    assert "forbidden" in v2_validator._system_prompt.lower()


def test_prompt_schema_version_v3_loads_combined_template():
    with patch(
        "app.core.validators.llm_utils.get_supported_openai_params",
        return_value=[],
    ):
        v3_validator = TopicRelevanceLLM(
            system_prompt=TOPIC_CONFIG, prompt_schema_version=3
        )

    assert "forbidden" in v3_validator._system_prompt.lower()
    assert "allowed" in v3_validator._system_prompt.lower()


def test_invalid_prompt_schema_version_returns_fail():
    with patch(
        "app.core.validators.llm_utils.get_supported_openai_params",
        return_value=[],
    ):
        invalid_version_validator = TopicRelevanceLLM(
            system_prompt=TOPIC_CONFIG, prompt_schema_version=99
        )

    result = invalid_version_validator._validate("Some input")

    assert isinstance(result, FailResult)
    assert "not found" in result.error_message
