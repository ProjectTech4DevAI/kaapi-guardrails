from unittest.mock import MagicMock, patch

import pytest

from app.core.validators import pii_remover
from app.core.validators.pii_remover import ALL_ENTITY_TYPES, DEFAULT_TRANSFORMERS_MODEL, DEFAULT_TRANSFORMERS_THRESHOLD, PIIRemover
from app.core.validators.config.pii_remover_safety_validator_config import PIIRemoverSafetyValidatorConfig

# -------------------------------
# Fixtures
# -------------------------------


@pytest.fixture
def mock_presidio():
    with patch(
        "app.core.validators.pii_remover._get_cached_analyzer"
    ) as mock_analyzer, patch(
        "app.core.validators.pii_remover.AnonymizerEngine"
    ) as mock_anonymizer:
        analyzer_instance = MagicMock()
        mock_analyzer.return_value = analyzer_instance
        anonymizer_instance = mock_anonymizer.return_value

        analyzer_instance.analyze.return_value = []
        anonymizer_instance.anonymize.return_value = MagicMock(text="original text")

        yield analyzer_instance, anonymizer_instance


@pytest.fixture
def validator(mock_presidio):
    return PIIRemover(entity_types=None, threshold=0.5)


# -------------------------------
# TESTS
# -------------------------------


def test_pass_when_no_pii_detected(validator):
    """
    If anonymized text is identical to input, should PASS.
    """
    result = validator._validate("original text")

    assert result.outcome == "pass"


def test_fail_when_pii_detected(validator):
    """
    If anonymized text differs, should FAIL with fix_value.
    """
    validator.anonymizer.anonymize.return_value = MagicMock(text="redacted text")

    result = validator._validate("original text")

    assert result.outcome == "fail"
    assert result.fix_value == "redacted text"
    assert result.error_message == "PII detected in the text."


def test_analyzer_called_with_correct_arguments(validator):
    validator._validate("hello")

    validator.analyzer.analyze.assert_called_once_with(
        text="hello",
        entities=validator.entity_types,
        language="en",
    )


def test_default_entity_types_applied(validator):
    assert validator.entity_types == ALL_ENTITY_TYPES


def test_custom_entity_types_override(mock_presidio):
    v = PIIRemover(entity_types=["EMAIL_ADDRESS"], threshold=0.5)

    assert v.entity_types == ["EMAIL_ADDRESS"]


def test_transformers_engine_uses_correct_defaults(mock_presidio):
    v = PIIRemover(nlp_engine_type="transformers")
    assert v.model_name == DEFAULT_TRANSFORMERS_MODEL
    assert v.threshold == DEFAULT_TRANSFORMERS_THRESHOLD


def test_spacy_engine_uses_correct_defaults(mock_presidio):
    v = PIIRemover(nlp_engine_type="spacy")
    assert v.model_name == "en_core_web_lg"
    assert v.threshold == 0.5


def test_transformers_engine_accepts_custom_model(mock_presidio):
    v = PIIRemover(nlp_engine_type="transformers", model_name="dslim/bert-base-NER-uncased")
    assert v.model_name == "dslim/bert-base-NER-uncased"


def test_config_builds_validator_with_nlp_engine_params(mock_presidio):
    config = PIIRemoverSafetyValidatorConfig(
        type="pii_remover",
        nlp_engine_type="transformers",
        model_name="dslim/bert-base-NER-uncased",
    )
    v = config.build()
    assert v.nlp_engine_type == "transformers"
    assert v.model_name == "dslim/bert-base-NER-uncased"


def test_config_defaults_to_spacy_engine(mock_presidio):
    config = PIIRemoverSafetyValidatorConfig(type="pii_remover")
    v = config.build()
    assert v.nlp_engine_type == "spacy"
    assert v.model_name == "en_core_web_lg"


def test_cached_analyzer_registers_only_requested_indian_recognizers():
    with patch(
        "app.core.validators.pii_remover._build_spacy_engine"
    ) as mock_build_engine, patch(
        "app.core.validators.pii_remover.AnalyzerEngine"
    ) as mock_analyzer:
        pii_remover._ANALYZER_CACHE.clear()
        pii_remover._NLP_ENGINE_CACHE.clear()
        analyzer_instance = mock_analyzer.return_value

        pii_remover._get_cached_analyzer(["EMAIL_ADDRESS", "IN_AADHAAR", "IN_PAN"], "spacy", "en_core_web_lg", 0.5)
        pii_remover._get_cached_analyzer(["EMAIL_ADDRESS", "IN_AADHAAR", "IN_PAN"], "spacy", "en_core_web_lg", 0.5)

        mock_build_engine.assert_called_once_with(pii_remover.SPACY_CONFIGURATION)
        mock_analyzer.assert_called_once()
        assert analyzer_instance.registry.add_recognizer.call_count == 2
