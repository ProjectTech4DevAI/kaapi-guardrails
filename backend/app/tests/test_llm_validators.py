from unittest.mock import patch

import pytest
from guardrails.validators import FailResult

from app.core.validators.config.topic_relevance_safety_validator_config import (
    TopicRelevanceSafetyValidatorConfig,
)
from app.core.validators.config.llm_critic_safety_validator_config import (
    LLMCriticSafetyValidatorConfig,
)
from app.api.routes.guardrails import _normalize_llm_critic_error

_SAMPLE_TOPIC_CONFIG = dict(
    type="topic_relevance",
    configuration="Only answer about cooking.",
    llm_callable="gpt-4o-mini",
)

_TOPIC_RELEVANCE_SETTINGS_PATH = (
    "app.core.validators.config.topic_relevance_safety_validator_config.settings"
)


def test_topic_relevance_build_raises_when_openai_key_missing():
    config = TopicRelevanceSafetyValidatorConfig(**_SAMPLE_TOPIC_CONFIG)

    with patch(_TOPIC_RELEVANCE_SETTINGS_PATH) as mock_settings:
        mock_settings.OPENAI_API_KEY = None

        with pytest.raises(ValueError) as exc:
            config.build()

    assert "OPENAI_API_KEY" in str(exc.value)
    assert "not configured" in str(exc.value)


def test_topic_relevance_build_proceeds_when_openai_key_present():
    config = TopicRelevanceSafetyValidatorConfig(**_SAMPLE_TOPIC_CONFIG)

    with patch(_TOPIC_RELEVANCE_SETTINGS_PATH) as mock_settings, patch(
        "app.core.validators.config.topic_relevance_safety_validator_config.TopicRelevance"
    ) as mock_validator:
        mock_settings.OPENAI_API_KEY = "sk-test-key"
        config.build()

    mock_validator.assert_called_once()


def test_topic_relevance_blank_config_returns_fail_result():
    config = TopicRelevanceSafetyValidatorConfig(
        **{**_SAMPLE_TOPIC_CONFIG, "configuration": None}
    )

    with patch(_TOPIC_RELEVANCE_SETTINGS_PATH) as mock_settings:
        mock_settings.OPENAI_API_KEY = "sk-test-key"
        validator = config.build()

    result = validator._validate("some input")
    assert isinstance(result, FailResult)
    assert "blank" in result.error_message


_SAMPLE_CONFIG = dict(
    type="llm_critic",
    metrics={
        "quality": {"description": "Is the response high quality?", "threshold": 2}
    },
    max_score=3,
    llm_callable="gpt-4o-mini",
)


def test_llm_critic_build_raises_when_openai_key_missing():
    config = LLMCriticSafetyValidatorConfig(**_SAMPLE_CONFIG)

    with patch(
        "app.core.validators.config.llm_critic_safety_validator_config.settings"
    ) as mock_settings:
        mock_settings.OPENAI_API_KEY = None

        with pytest.raises(ValueError) as exc:
            config.build()

    assert "OPENAI_API_KEY" in str(exc.value)
    assert "not configured" in str(exc.value)


def test_llm_critic_build_proceeds_when_openai_key_present():
    config = LLMCriticSafetyValidatorConfig(**_SAMPLE_CONFIG)

    with patch(
        "app.core.validators.config.llm_critic_safety_validator_config.settings"
    ) as mock_settings, patch(
        "app.core.validators.config.llm_critic_safety_validator_config.LLMCritic"
    ) as mock_llm_critic:
        mock_settings.OPENAI_API_KEY = "sk-test-key"
        config.build()

    mock_llm_critic.assert_called_once()


def test__normalize_llm_critic_error_maps_failed_metrics():
    raw = "The response failed the following metrics: ['quality']."
    result = _normalize_llm_critic_error(raw)
    assert result == "The response did not meet the required quality criteria."


def test__normalize_llm_critic_error_maps_missing_invalid_metrics():
    raw = "The response is missing or has invalid evaluations for the following metrics: ['quality']."
    result = _normalize_llm_critic_error(raw)
    assert "could not evaluate" in result
    assert "Please retry" in result


def test__normalize_llm_critic_error_passes_through_unknown_messages():
    raw = "Some other validator error."
    assert _normalize_llm_critic_error(raw) == raw
