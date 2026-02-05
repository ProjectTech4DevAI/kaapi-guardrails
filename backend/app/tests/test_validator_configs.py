import uuid
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import Session, delete

from app.api.routes.validator_configs import (
    flatten_validator,
    get_validator_or_404,
    update_validator_config,
)
from app.core.enum import GuardrailOnFail, Stage, ValidatorType
from app.core.db import engine
from app.models.config.validator_config_table import ValidatorConfig

# Test data constants
TEST_ORG_ID = 1
TEST_PROJECT_ID = 1
TEST_VALIDATOR_ID = uuid.uuid4()
TEST_TYPE = ValidatorType.LexicalSlur
TEST_STAGE = Stage.Input
TEST_ON_FAIL = GuardrailOnFail.Fix


@pytest.fixture
def clear_database():
    """Clear ValidatorConfig table before and after each test."""
    with Session(engine) as session:
        session.exec(delete(ValidatorConfig))
        session.commit()
    yield
    with Session(engine) as session:
        session.exec(delete(ValidatorConfig))
        session.commit()


@pytest.fixture
def mock_session():
    """Create a mock session for database operations."""
    return MagicMock(spec=Session)


@pytest.fixture
def sample_validator():
    """Create a sample validator config for testing."""
    return ValidatorConfig(
        id=TEST_VALIDATOR_ID,
        org_id=TEST_ORG_ID,
        project_id=TEST_PROJECT_ID,
        type=TEST_TYPE,
        stage=TEST_STAGE,
        on_fail_action=TEST_ON_FAIL,
        is_enabled=True,
        config={"severity": "all", "languages": ["en", "hi"]},
    )


class TestFlattenValidator:
    """Tests for flatten_validator helper function."""

    def test_flatten_validator_includes_config_fields(self, sample_validator):
        """Test that flatten_validator includes config fields in output."""
        result = flatten_validator(sample_validator)

        assert result["id"] == TEST_VALIDATOR_ID
        assert result["org_id"] == TEST_ORG_ID
        assert result["project_id"] == TEST_PROJECT_ID
        assert result["type"] == TEST_TYPE
        assert result["severity"] == "all"
        assert result["languages"] == ["en", "hi"]

    def test_flatten_validator_with_empty_config(self):
        """Test flatten_validator with empty config dict."""
        validator = ValidatorConfig(
            id=TEST_VALIDATOR_ID,
            org_id=TEST_ORG_ID,
            project_id=TEST_PROJECT_ID,
            type=TEST_TYPE,
            stage=TEST_STAGE,
            on_fail_action=TEST_ON_FAIL,
            is_enabled=True,
            config={},
        )

        result = flatten_validator(validator)

        assert result["id"] == TEST_VALIDATOR_ID
        assert "severity" not in result
        # Base fields: id, org_id, project_id, type, stage, on_fail_action, is_enabled, created_at, updated_at
        assert len(result) == 9

    def test_flatten_validator_with_none_config(self):
        """Test flatten_validator with None config."""
        validator = ValidatorConfig(
            id=TEST_VALIDATOR_ID,
            org_id=TEST_ORG_ID,
            project_id=TEST_PROJECT_ID,
            type=TEST_TYPE,
            stage=TEST_STAGE,
            on_fail_action=TEST_ON_FAIL,
            is_enabled=True,
            config=None,
        )

        result = flatten_validator(validator)

        assert result["id"] == TEST_VALIDATOR_ID
        assert "severity" not in result


class TestGetValidatorOr404:
    """Tests for get_validator_or_404 helper function."""

    def test_get_validator_success(self, sample_validator, mock_session):
        """Test successful validator retrieval."""
        mock_session.query.return_value.filter.return_value.first.return_value = (
            sample_validator
        )

        result = get_validator_or_404(
            TEST_VALIDATOR_ID, TEST_ORG_ID, TEST_PROJECT_ID, mock_session
        )

        assert result == sample_validator
        mock_session.query.assert_called_once_with(ValidatorConfig)

    def test_get_validator_not_found(self, mock_session):
        """Test validator not found raises 404."""
        mock_session.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(Exception) as exc_info:
            get_validator_or_404(TEST_VALIDATOR_ID, TEST_ORG_ID, TEST_PROJECT_ID, mock_session)

        assert "404" in str(exc_info.value)


class TestUpdateValidatorConfig:
    """Tests for update_validator_config helper function."""

    def test_update_validator_config_base_fields(self, sample_validator, mock_session):
        """Test updating base validator fields."""
        update_data = {
            "type": ValidatorType.PIIRemover,
            "on_fail_action": GuardrailOnFail.Exception,
        }

        result = update_validator_config(sample_validator, update_data, mock_session)

        assert result.type == ValidatorType.PIIRemover
        assert result.on_fail_action == GuardrailOnFail.Exception
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    def test_update_validator_config_extra_fields(self, sample_validator, mock_session):
        """Test updating extra config fields."""
        update_data = {"severity": "high", "new_field": "new_value"}

        result = update_validator_config(sample_validator, update_data, mock_session)

        assert result.config["severity"] == "high"
        assert result.config["new_field"] == "new_value"
        assert result.config["languages"] == ["en", "hi"]  # Original values preserved

    def test_update_validator_merges_config(self, sample_validator, mock_session):
        """Test that updating config merges with existing config."""
        sample_validator.config = {"severity": "all", "languages": ["en"]}
        update_data = {"languages": ["en", "hi", "mr"]}

        result = update_validator_config(sample_validator, update_data, mock_session)

        assert result.config["languages"] == ["en", "hi", "mr"]
        assert result.config["severity"] == "all"

