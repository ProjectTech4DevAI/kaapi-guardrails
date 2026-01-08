import pandas as pd
import pytest
from unittest.mock import patch

from app.core.enum import BiasCategories
from app.core.validators.gender_assumption_bias import GenderAssumptionBias
from guardrails.validators import FailResult, PassResult

@pytest.fixture
def mock_gender_bias_df():
    return pd.DataFrame([
        {"word": "he", "neutral-term": "they", "type": "pronoun"},
        {"word": "she", "neutral-term": "they", "type": "pronoun"},
        {"word": "policeman", "neutral-term": "police officer", "type": "generic"},
    ])

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
    assert result.fix_value == "they is a police officer."

def test_case_insensitive_bias_detection(validator):
    result = validator._validate("SHE is honest.")
    assert isinstance(result, FailResult)
    assert "she" in result.error_message.lower()
    assert result.fix_value == "they is honest."

def test_word_boundary_not_partial_match(validator):
    result = validator._validate("The theme was good.")
    assert isinstance(result, PassResult)

def test_multiple_gender_biases_detected(validator):
    result = validator._validate("He and she are working.")
    assert isinstance(result, FailResult)
    assert "he" in result.error_message.lower()
    assert "she" in result.error_message.lower()
    assert result.fix_value == "they and they are working."

def test_category_filtering(mock_gender_bias_df):
    with patch("pandas.read_csv", return_value=mock_gender_bias_df):
        validator = GenderAssumptionBias(categories=[BiasCategories.Generic])

    result = validator._validate("He is a policeman.")
    # Only profession bias should apply
    assert isinstance(result, FailResult)
    assert result.fix_value == "He is a police officer."

def test_missing_gender_bias_file_raises_error():
    with patch("pandas.read_csv", side_effect=FileNotFoundError):
        with pytest.raises(FileNotFoundError):
            GenderAssumptionBias(categories=[BiasCategories.All])

def test_csv_load_failure_raises_value_error():
    with patch("pandas.read_csv", side_effect=Exception("boom")):
        with pytest.raises(ValueError):
            GenderAssumptionBias(categories=[BiasCategories.All])
