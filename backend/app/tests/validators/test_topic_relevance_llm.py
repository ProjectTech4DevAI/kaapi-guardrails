from unittest.mock import MagicMock, patch

import pytest
from guardrails.validators import FailResult, PassResult

from app.core.constants import REPHRASE_ON_FAIL_PREFIX
from app.core.enum import GuardrailOnFail
from app.core.validators.config.topic_relevance_llm_safety_validator_config import (
    TopicRelevanceLLMSafetyValidatorConfig,
)
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


def test_fails_when_score_is_1(validator):
    with patch("app.core.validators.topic_relevance_llm.completion") as mock_llm:
        mock_llm.return_value = _make_llm_response('{"scope_violation": 1}')
        result = validator._validate("What is the latest cricket score?")

    assert isinstance(result, FailResult)
    assert "outside the allowed topic scope" in result.error_message
    assert result.metadata["scope_score"] == 1


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


def test_fails_gracefully_when_llm_raises(validator):
    with patch(
        "app.core.validators.topic_relevance_llm.completion",
        side_effect=Exception("network timeout"),
    ):
        result = validator._validate("How do I bake bread?")

    assert isinstance(result, FailResult)
    assert "LLM call failed" in result.error_message
    assert "network timeout" in result.error_message


def test_fails_gracefully_when_content_is_none(validator):
    # Reasoning models (gpt-5.6-sol) return content=None when the budget is
    # spent on hidden reasoning; must surface as unparseable, not a crash.
    with patch("app.core.validators.topic_relevance_llm.completion") as mock_llm:
        mock_llm.return_value = _make_llm_response(None)
        result = validator._validate("How do I bake bread?")

    assert isinstance(result, FailResult)
    assert "unparseable" in result.error_message


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


def test_user_message_is_exactly_the_query(validator):
    query = "How do I make pasta?"
    with patch("app.core.validators.topic_relevance_llm.completion") as mock_llm:
        mock_llm.return_value = _make_llm_response('{"scope_violation": 3}')
        validator._validate(query)

    _, kwargs = mock_llm.call_args
    user_message = kwargs["messages"][1]["content"]
    assert user_message == query


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


def test_system_prompt_contains_topic_config():
    with patch(
        "app.core.validators.llm_utils.get_supported_openai_params",
        return_value=[],
    ):
        validator = TopicRelevanceLLM(system_prompt=TOPIC_CONFIG)

    assert TOPIC_CONFIG in validator._system_prompt
    # The config must be labelled and sit below the instructions: a bare
    # keyword list gave the model no way to know it was reading a topic list.
    prompt = validator._system_prompt
    assert prompt.index("# Instructions") < prompt.index(
        "<allowed_topics>\n" + TOPIC_CONFIG
    )
    assert prompt.index(TOPIC_CONFIG + "\n</allowed_topics>") > prompt.index(
        "# Examples"
    )
    assert "{{TOPIC_CONFIGURATION}}" not in validator._system_prompt


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


def test_config_defaults_to_forbidden_topics_schema():
    config = TopicRelevanceLLMSafetyValidatorConfig(type="topic_relevance_llm")
    assert config.prompt_schema_version == 2
    assert config.on_fail == GuardrailOnFail.Rephrase


def test_config_rephrase_without_fallback_uses_generic_text():
    config = TopicRelevanceLLMSafetyValidatorConfig(
        type="topic_relevance_llm", on_fail="rephrase"
    )
    on_fail = config.resolve_on_fail()
    assert on_fail("Who won?", FailResult(error_message="out of scope")).startswith(
        REPHRASE_ON_FAIL_PREFIX
    )


FALLBACK = "I can only help with cooking questions."


def _fallback_validator(**kwargs):
    with patch(
        "app.core.validators.llm_utils.get_supported_openai_params",
        return_value=["response_format"],
    ):
        return TopicRelevanceLLM(
            system_prompt=TOPIC_CONFIG, fallback_message=FALLBACK, **kwargs
        )


def test_fallback_instructions_added_to_system_prompt():
    validator = _fallback_validator()
    assert "localized_fallback" in validator._system_prompt
    assert FALLBACK in validator._system_prompt


def test_fallback_raises_max_tokens():
    validator = _fallback_validator()
    with patch("app.core.validators.topic_relevance_llm.completion") as mock_llm:
        mock_llm.return_value = _make_llm_response('{"scope_violation": 3}')
        validator._validate("How do I make pasta?")

    assert mock_llm.call_args.kwargs["max_tokens"] == 600


def test_localized_fallback_exposed_in_fail_metadata():
    validator = _fallback_validator()
    with patch("app.core.validators.topic_relevance_llm.completion") as mock_llm:
        mock_llm.return_value = _make_llm_response(
            '{"scope_violation": 1, "localized_fallback": "मैं केवल खाना पकाने में मदद कर सकता हूँ।"}'
        )
        result = validator._validate("क्रिकेट मैच किसने जीता?")

    assert isinstance(result, FailResult)
    assert (
        result.metadata["localized_fallback"]
        == "मैं केवल खाना पकाने में मदद कर सकता हूँ।"
    )


def test_config_rephrase_prefers_localized_fallback():
    config = TopicRelevanceLLMSafetyValidatorConfig(
        type="topic_relevance_llm", on_fail="rephrase", fallback_message=FALLBACK
    )
    on_fail = config.resolve_on_fail()
    fail = FailResult(
        error_message="out of scope", metadata={"localized_fallback": " नमस्ते "}
    )
    assert on_fail("x", fail) == "नमस्ते"


@pytest.mark.parametrize("localized", [None, "", "   ", 123, {"text": "hi"}])
def test_config_rephrase_ignores_invalid_localized_fallback(localized):
    config = TopicRelevanceLLMSafetyValidatorConfig(
        type="topic_relevance_llm", on_fail="rephrase", fallback_message=FALLBACK
    )
    on_fail = config.resolve_on_fail()
    fail = FailResult(
        error_message="out of scope", metadata={"localized_fallback": localized}
    )
    assert on_fail("x", fail) == FALLBACK
