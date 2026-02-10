import uuid
from unittest.mock import MagicMock

import pytest
from sqlmodel import Session

from app.crud.validator_config import validator_config_crud
from app.core.enum import GuardrailOnFail, Stage, ValidatorType
from app.models.config.validator_config import ValidatorConfig

# Test data constants
TEST_ORGANIZATION_ID = 1
TEST_PROJECT_ID = 1
TEST_VALIDATOR_ID = uuid.uuid4()
TEST_TYPE = ValidatorType.LexicalSlur
TEST_STAGE = Stage.Input
TEST_ON_FAIL = GuardrailOnFail.Fix


@pytest.fixture
def mock_session():
    """Create a mock session for database operations."""
    return MagicMock(spec=Session)


@pytest.fixture
def sample_validator():
    """Create a sample validator config for testing."""
    return ValidatorConfig(
        id=TEST_VALIDATOR_ID,
        organization_id=TEST_ORGANIZATION_ID,
        project_id=TEST_PROJECT_ID,
        type=TEST_TYPE,
        stage=TEST_STAGE,
        on_fail_action=TEST_ON_FAIL,
        is_enabled=True,
        config={"severity": "all", "languages": ["en", "hi"]},
    )


class TestFlatten:
    def test_flatten_includes_config_fields(self, sample_validator):
        result = validator_config_crud.flatten(sample_validator)

        assert result["severity"] == "all"
        assert result["languages"] == ["en", "hi"]
        assert result["id"] == TEST_VALIDATOR_ID

    def test_flatten_empty_config(self):
        validator = ValidatorConfig(
            id=TEST_VALIDATOR_ID,
            organization_id=TEST_ORGANIZATION_ID,
            project_id=TEST_PROJECT_ID,
            type=TEST_TYPE,
            stage=TEST_STAGE,
            on_fail_action=TEST_ON_FAIL,
            is_enabled=True,
            config={},
        )

        result = validator_config_crud.flatten(validator)

        assert "severity" not in result


class TestGetOr404:
    def test_success(self, sample_validator, mock_session):
        mock_session.get.return_value = sample_validator

        result = validator_config_crud.get(
            mock_session,
            TEST_VALIDATOR_ID,
            TEST_ORGANIZATION_ID,
            TEST_PROJECT_ID,
        )

        assert result == sample_validator
        mock_session.get.assert_called_once()

    def test_not_found(self, mock_session):
        mock_session.get.return_value = None

        with pytest.raises(Exception) as exc:
            validator_config_crud.get(
                mock_session,
                TEST_VALIDATOR_ID,
                TEST_ORGANIZATION_ID,
                TEST_PROJECT_ID,
            )

        assert "Validator not found" in str(exc.value)


class TestUpdate:
    def test_update_base_fields(self, sample_validator, mock_session):
        update_data = {
            "type": ValidatorType.PIIRemover,
            "on_fail_action": GuardrailOnFail.Exception,
        }

        result = validator_config_crud.update(
            mock_session,
            sample_validator,
            update_data,
        )

        assert result["type"] == ValidatorType.PIIRemover
        assert result["on_fail_action"] == GuardrailOnFail.Exception

        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    def test_update_extra_fields(self, sample_validator, mock_session):
        update_data = {"severity": "high", "new_field": "new_value"}

        result = validator_config_crud.update(
            mock_session,
            sample_validator,
            update_data,
        )

        assert result["severity"] == "high"
        assert result["new_field"] == "new_value"
        assert result["languages"] == ["en", "hi"]

    def test_merge_config(self, sample_validator, mock_session):
        sample_validator.config = {"severity": "all", "languages": ["en"]}

        result = validator_config_crud.update(
            mock_session,
            sample_validator,
            {"languages": ["en", "hi"]},
        )

        assert result["languages"] == ["en", "hi"]
        assert result["severity"] == "all"
