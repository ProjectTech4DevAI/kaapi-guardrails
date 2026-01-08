import pytest
from uuid import uuid4

from fastapi.responses import JSONResponse
from unittest.mock import patch, MagicMock

from app.api.routes.guardrails import _validate_with_guard
from app.tests.guardrails_mocks import MockResult, MockFailure

mock_request_log_crud = MagicMock()
mock_request_log_id = uuid4()

@pytest.mark.asyncio
async def test_validate_with_guard_success(client):
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
            response_field="safe_input",
            request_log_crud=mock_request_log_crud,
            request_log_id=mock_request_log_id,
        )

    assert response.success is True
    assert response.data["safe_input"] == "clean text"
    assert "response_id" in response.data

@pytest.mark.asyncio
async def test_validate_with_guard_validation_error_with_failures():
    class MockGuard:
        def validate(self, data):
            return MockResult(
                validated_output=None,
                failures=[MockFailure("PII detected")]
            )

    with patch(
        "app.api.routes.guardrails.build_guard",
        return_value=MockGuard(),
    ):
        response = await _validate_with_guard(
            data="bad text",
            validators=[],
            response_field="safe_input",
            request_log_crud=mock_request_log_crud,
            request_log_id=mock_request_log_id,
        )

    assert isinstance(response, JSONResponse)
    assert response.status_code == 400

    body = response.body.decode()
    assert "validation_error" in body
    assert "reask" in body
    assert "PII detected" in body

@pytest.mark.asyncio
async def test_validate_with_guard_validation_error_no_failures():
    class MockGuard:
        def validate(self, data):
            return MockResult(validated_output=None, failures=[])

    with patch(
        "app.api.routes.guardrails.build_guard",
        return_value=MockGuard(),
    ):
        response = await _validate_with_guard(
            data="bad text",
            validators=[],
            response_field="safe_output",
            request_log_crud=mock_request_log_crud,
            request_log_id=mock_request_log_id,
        )

    assert response.status_code == 400

    body = response.body.decode()
    assert "validation_error" in body
    assert "fail" in body

@pytest.mark.asyncio
async def test_validate_with_guard_exception():
    with patch(
        "app.api.routes.guardrails.build_guard",
        side_effect=Exception("Invalid config"),
    ):
        response = await _validate_with_guard(
            data="text",
            validators=[],
            response_field="safe_input",
            request_log_crud=mock_request_log_crud,
            request_log_id=mock_request_log_id,
        )

    assert response.status_code == 500

    body = response.body.decode()
    assert "config_error" in body
    assert "Invalid config" in body