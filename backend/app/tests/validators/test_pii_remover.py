from unittest.mock import MagicMock, patch

import pytest

from app.core.validators import pii_remover
from app.core.validators.pii_remover import ALL_ENTITY_TYPES, PIIRemover

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


def test_cached_analyzer_registers_only_requested_indian_recognizers():
    with patch(
        "app.core.validators.pii_remover.NlpEngineProvider"
    ) as mock_provider, patch(
        "app.core.validators.pii_remover.AnalyzerEngine"
    ) as mock_analyzer:
        pii_remover._ANALYZER_CACHE.clear()
        pii_remover._GLOBAL_NLP_ENGINE = None
        analyzer_instance = mock_analyzer.return_value

        pii_remover._get_cached_analyzer(["EMAIL_ADDRESS", "IN_AADHAAR", "IN_PAN"])
        pii_remover._get_cached_analyzer(["EMAIL_ADDRESS", "IN_AADHAAR", "IN_PAN"])

        mock_provider.assert_called_once_with(
            nlp_configuration=pii_remover.CONFIGURATION
        )
        mock_provider.return_value.create_engine.assert_called_once()
        mock_analyzer.assert_called_once()
        assert analyzer_instance.registry.add_recognizer.call_count == 2
