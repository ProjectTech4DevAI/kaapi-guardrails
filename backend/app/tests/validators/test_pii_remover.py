from unittest.mock import MagicMock, patch

import pytest

from app.core.validators.pii_remover import ALL_ENTITY_TYPES, PIIRemover


# -------------------------------
# Fixtures
# -------------------------------


@pytest.fixture
def mock_presidio():
    """
    Mock AnalyzerEngine and AnonymizerEngine before validator loads.
    """
    with patch(
        "app.core.validators.pii_remover.AnalyzerEngine"
    ) as mock_analyzer, patch(
        "app.core.validators.pii_remover.AnonymizerEngine"
    ) as mock_anonymizer:
        analyzer_instance = mock_analyzer.return_value
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


def test_indian_recognizers_registered_when_requested():
    """
    Ensure Indian recognizers are conditionally registered.
    """
    with patch(
        "app.core.validators.pii_remover.AnalyzerEngine"
    ) as mock_analyzer, patch("app.core.validators.pii_remover.AnonymizerEngine"):
        registry = mock_analyzer.return_value.registry

        PIIRemover(
            entity_types=[
                "IN_AADHAAR",
                "IN_PAN",
                "IN_PASSPORT",
                "IN_VEHICLE_REGISTRATION",
                "IN_VOTER",
            ],
            threshold=0.5,
        )

        # Called once per recognizer
        assert registry.add_recognizer.call_count == 5
