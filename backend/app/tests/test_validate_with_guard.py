from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.api.routes.guardrails import _validate_with_guard
from app.schemas.guardrail_config import GuardrailRequest
from app.tests.guardrails_mocks import MockResult
from app.tests.seed_data import (
    VALIDATOR_TEST_ORGANIZATION_ID,
    VALIDATOR_TEST_PROJECT_ID,
)
from app.utils import APIResponse


mock_request_log_crud = MagicMock()
mock_validator_log_crud = MagicMock()
mock_request_log_id = uuid4()


def _build_payload(input_text: str) -> GuardrailRequest:
    return GuardrailRequest(
        request_id=str(uuid4()),
        organization_id=VALIDATOR_TEST_ORGANIZATION_ID,
        project_id=VALIDATOR_TEST_PROJECT_ID,
        input=input_text,
        validators=[],
    )


def test_validate_with_guard_success():
    class MockGuard:
        def validate(self, data):
            return MockResult(validated_output="clean text")

    with patch(
        "app.api.routes.guardrails.build_guard",
        return_value=MockGuard(),
    ):
        response = _validate_with_guard(
            payload=_build_payload("hello"),
            request_log_crud=mock_request_log_crud,
            request_log_id=mock_request_log_id,
            validator_log_crud=mock_validator_log_crud,
        )

    assert isinstance(response, APIResponse)
    assert response.success is True
    assert response.data.safe_text == "clean text"
    assert response.data.response_id is not None


def test_validate_with_guard_validation_error():
    class MockGuard:
        def validate(self, data):
            return MockResult(validated_output=None)

    with patch(
        "app.api.routes.guardrails.build_guard",
        return_value=MockGuard(),
    ):
        response = _validate_with_guard(
            payload=_build_payload("bad text"),
            request_log_crud=mock_request_log_crud,
            request_log_id=mock_request_log_id,
            validator_log_crud=mock_validator_log_crud,
        )

    assert isinstance(response, APIResponse)
    assert response.success is False
    assert response.data.safe_text is None
    assert response.error


def test_validate_with_guard_exception():
    with patch(
        "app.api.routes.guardrails.build_guard",
        side_effect=Exception("Invalid config"),
    ):
        response = _validate_with_guard(
            payload=_build_payload("text"),
            request_log_crud=mock_request_log_crud,
            request_log_id=mock_request_log_id,
            validator_log_crud=mock_validator_log_crud,
        )

    assert isinstance(response, APIResponse)
    assert response.success is False
    assert response.data.safe_text is None
    assert response.error == "Invalid config"
