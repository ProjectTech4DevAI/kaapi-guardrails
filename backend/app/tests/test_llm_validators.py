from unittest.mock import patch

import pytest
from guardrails.validators import FailResult

from app.core.validators.config.answer_relevance_custom_llm_safety_validator_config import (
    AnswerRelevanceCustomLLMSafetyValidatorConfig,
)
from app.core.validators.config.topic_relevance_safety_validator_config import (
    TopicRelevanceSafetyValidatorConfig,
)
from app.core.validators.config.topic_relevance_llm_safety_validator_config import (
    TopicRelevanceLLMSafetyValidatorConfig,
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


_SAMPLE_LLM_TOPIC_CONFIG = dict(
    type="topic_relevance_llm",
    configuration="Only answer about cooking.",
    llm_callable="gpt-4o-mini",
)

_TOPIC_RELEVANCE_LLM_SETTINGS_PATH = (
    "app.core.validators.config.topic_relevance_llm_safety_validator_config.settings"
)


def test_topic_relevance_llm_build_raises_when_openai_key_missing():
    config = TopicRelevanceLLMSafetyValidatorConfig(**_SAMPLE_LLM_TOPIC_CONFIG)

    with patch(_TOPIC_RELEVANCE_LLM_SETTINGS_PATH) as mock_settings:
        mock_settings.OPENAI_API_KEY = None

        with pytest.raises(ValueError) as exc:
            config.build()

    assert "OPENAI_API_KEY" in str(exc.value)
    assert "not configured" in str(exc.value)


def test_topic_relevance_llm_build_proceeds_when_openai_key_present():
    config = TopicRelevanceLLMSafetyValidatorConfig(**_SAMPLE_LLM_TOPIC_CONFIG)

    with patch(_TOPIC_RELEVANCE_LLM_SETTINGS_PATH) as mock_settings, patch(
        "app.core.validators.config.topic_relevance_llm_safety_validator_config.TopicRelevanceLLM"
    ) as mock_validator:
        mock_settings.OPENAI_API_KEY = "sk-test-key"
        config.build()

    mock_validator.assert_called_once()


def test_topic_relevance_llm_blank_config_returns_fail_result():
    config = TopicRelevanceLLMSafetyValidatorConfig(
        **{**_SAMPLE_LLM_TOPIC_CONFIG, "configuration": None}
    )

    with patch(_TOPIC_RELEVANCE_LLM_SETTINGS_PATH) as mock_settings, patch(
        "app.core.validators.llm_utils.get_supported_openai_params",
        return_value=[],
    ):
        mock_settings.OPENAI_API_KEY = "sk-test-key"
        validator = config.build()

    result = validator._validate("some input")
    assert isinstance(result, FailResult)
    assert "blank" in result.error_message


def test_topic_relevance_llm_default_threshold_is_2():
    config = TopicRelevanceLLMSafetyValidatorConfig(**_SAMPLE_LLM_TOPIC_CONFIG)
    assert config.threshold == 2


def test_topic_relevance_llm_custom_threshold_forwarded_to_validator():
    config = TopicRelevanceLLMSafetyValidatorConfig(
        **{**_SAMPLE_LLM_TOPIC_CONFIG, "threshold": 3}
    )

    with patch(_TOPIC_RELEVANCE_LLM_SETTINGS_PATH) as mock_settings, patch(
        "app.core.validators.config.topic_relevance_llm_safety_validator_config.TopicRelevanceLLM"
    ) as mock_validator:
        mock_settings.OPENAI_API_KEY = "sk-test-key"
        config.build()

    call_kwargs = mock_validator.call_args[1]
    assert call_kwargs["threshold"] == 3
