from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.api.routes.guardrails import _validate_with_guard
from app.tests.guardrails_mocks import MockResult
from app.utils import APIResponse


mock_request_log_crud = MagicMock()
mock_validator_log_crud = MagicMock()
mock_request_log_id = uuid4()


@pytest.mark.asyncio
async def test_validate_with_guard_success():
    class MockGuard:
        def validate(self, data):
            return MockResult(validated_output="clean text")

    with patch(
        "app.api.routes.guardrails.build_guard",
        return_value=MockGuard(),
    ):
        response = await _validate_with_guard(
            data="hello",
            validators=[],
            request_log_crud=mock_request_log_crud,
            request_log_id=mock_request_log_id,
            validator_log_crud=mock_validator_log_crud,
        )

    assert isinstance(response, APIResponse)
    assert response.success is True
    assert response.data.safe_text == "clean text"
    assert response.data.response_id is not None


@pytest.mark.asyncio
async def test_validate_with_guard_validation_error():
    class MockGuard:
        def validate(self, data):
            return MockResult(validated_output=None)

    with patch(
        "app.api.routes.guardrails.build_guard",
        return_value=MockGuard(),
    ):
        response = await _validate_with_guard(
            data="bad text",
            validators=[],
            request_log_crud=mock_request_log_crud,
            request_log_id=mock_request_log_id,
            validator_log_crud=mock_validator_log_crud,
        )

    assert isinstance(response, APIResponse)
    assert response.success is False
    assert response.data.safe_text is None
    assert response.error


@pytest.mark.asyncio
async def test_validate_with_guard_exception():
    with patch(
        "app.api.routes.guardrails.build_guard",
        side_effect=Exception("Invalid config"),
    ):
        response = await _validate_with_guard(
            data="text",
            validators=[],
            request_log_crud=mock_request_log_crud,
            request_log_id=mock_request_log_id,
            validator_log_crud=mock_validator_log_crud,
        )

    assert isinstance(response, APIResponse)
    assert response.success is False
    assert response.data.safe_text is None
    assert response.error == "Invalid config"
