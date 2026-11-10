import pandas as pd
import pytest
from unittest.mock import patch

from app.core.enum import BiasCategories
from app.core.validators.gender_assumption_bias import GenderAssumptionBias
from guardrails.validators import FailResult, PassResult


@pytest.fixture
def mock_gender_bias_df():
    return pd.DataFrame(
        [
            {"word": "he", "neutral-term": "they", "type": "pronoun"},
            {"word": "she", "neutral-term": "they", "type": "pronoun"},
            {"word": "policeman", "neutral-term": "police officer", "type": "generic"},
        ]
    )


@pytest.fixture
def validator(mock_gender_bias_df):
    with patch("pandas.read_csv", return_value=mock_gender_bias_df):
        return GenderAssumptionBias(categories=[BiasCategories.All])


def test_pass_when_no_gender_bias_detected(validator):
    result = validator._validate("This person is very kind.")
    assert isinstance(result, PassResult)


def test_fail_when_gender_bias_detected(validator):
    result = validator._validate("He is a great engineer.")
    assert isinstance(result, FailResult)
    assert "he" in result.error_message.lower()


def test_replaces_biased_word_with_neutral_term(validator):
    result = validator._validate("He is a policeman.")
    assert isinstance(result, FailResult)
    assert result.fix_value == "They is a police officer."


def test_case_insensitive_bias_detection(validator):
    result = validator._validate("SHE is honest.")
    assert isinstance(result, FailResult)
    assert "she" in result.error_message.lower()
    assert result.fix_value == "THEY is honest."


def test_word_boundary_not_partial_match(validator):
    result = validator._validate("The theme was good.")
    assert isinstance(result, PassResult)


def test_multiple_gender_biases_detected(validator):
    result = validator._validate("He and she are working.")
    assert isinstance(result, FailResult)
    assert "he" in result.error_message.lower()
    assert "she" in result.error_message.lower()
    assert result.fix_value == "They and they are working."


def test_category_filtering(mock_gender_bias_df):
    with patch("pandas.read_csv", return_value=mock_gender_bias_df):
        validator = GenderAssumptionBias(categories=[BiasCategories.Generic])

    result = validator._validate("He is a policeman.")
    # Only profession bias should apply
    assert isinstance(result, FailResult)
    assert result.fix_value == "He is a police officer."


@pytest.fixture
def full_validator():
    """Validator over a word list that mirrors the real CSV's tricky rows."""
    df = pd.DataFrame(
        [
            {"word": "her", "neutral-term": "them", "type": "generic"},
            {"word": "woh", "neutral-term": "woh", "type": "generic"},
            {"word": "midwife", "neutral-term": "birth attendant", "type": "healthcare"},
            {"word": "attendant", "neutral-term": "attendant", "type": "healthcare"},
            {"word": "छात्र", "neutral-term": "विद्यार्थी", "type": "education"},
            {"word": "छात्रा", "neutral-term": "विद्यार्थी", "type": "education"},
            {"word": "गया", "neutral-term": "गए", "type": "generic"},
        ]
    )
    with patch("pandas.read_csv", return_value=df):
        return GenderAssumptionBias(categories=[BiasCategories.All])


def test_identity_mappings_do_not_flag_neutral_text(full_validator):
    assert isinstance(full_validator._validate("Woh apni file submit kar gaye."), PassResult)
    assert isinstance(
        full_validator._validate("The birth attendant checked their patient."), PassResult
    )


def test_replacement_is_not_rematched_by_identity_row(full_validator):
    result = full_validator._validate("The midwife arrived.")
    assert result.fix_value == "The birth attendant arrived."
    assert result.error_message == "Detected gender assumption bias: ['midwife']"


def test_possessive_her_becomes_their(full_validator):
    result = full_validator._validate("The midwife checked her patient carefully.")
    assert result.fix_value == "The birth attendant checked their patient carefully."


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Please help her.", "Please help them."),
        ("Give her the report.", "Give them the report."),
        ("Her report is ready.", "Their report is ready."),
    ],
)
def test_object_and_possessive_her(full_validator, text, expected):
    assert full_validator._validate(text).fix_value == expected


def test_devanagari_word_not_matched_inside_longer_word(full_validator):
    result = full_validator._validate("छात्रा ने कहा")
    assert result.fix_value == "विद्यार्थी ने कहा"


def test_devanagari_word_ending_in_vowel_sign_before_danda(full_validator):
    result = full_validator._validate("वे घर गया।")
    assert result.fix_value == "वे घर गए।"


def test_missing_gender_bias_file_raises_error():
    with patch("pandas.read_csv", side_effect=FileNotFoundError):
        with pytest.raises(FileNotFoundError):
            GenderAssumptionBias(categories=[BiasCategories.All])


def test_csv_load_failure_raises_value_error():
    with patch("pandas.read_csv", side_effect=Exception("boom")):
        with pytest.raises(ValueError):
            GenderAssumptionBias(categories=[BiasCategories.All])
