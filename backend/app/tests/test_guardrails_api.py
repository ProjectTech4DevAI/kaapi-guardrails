from unittest.mock import MagicMock, patch

import pytest

from app.tests.guardrails_mocks import MockResult
from app.tests.utils.constants import SAFE_TEXT_FIELD, VALIDATE_API_PATH

build_guard_path = "app.api.routes.guardrails.build_guard"
crud_path = "app.api.routes.guardrails.RequestLogCrud"

request_id = "123e4567-e89b-12d3-a456-426614174000"


@pytest.fixture
def mock_crud():
    with patch(crud_path) as mock:
        instance = mock.return_value
        instance.create.return_value = MagicMock(id=1)
        yield instance


def test_route_exists(client):
    paths = {route.path for route in client.app.routes}
    assert VALIDATE_API_PATH in paths


def test_validate_guardrails_success(client):
    class MockGuard:
        def validate(self, data):
            return MockResult(validated_output="clean text")

    with patch(build_guard_path, return_value=MockGuard()):
        response = client.post(
            VALIDATE_API_PATH,
            json={
                "request_id": request_id,
                "input": "hello world",
                "validators": [],
            },
        )

    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    assert body["data"][SAFE_TEXT_FIELD] == "clean text"
    assert "response_id" in body["data"]


def test_validate_guardrails_failure(client, mock_crud):
    class MockGuard:
        def validate(self, data):
            return MockResult(validated_output=None)

    with patch(build_guard_path, return_value=MockGuard()):
        response = client.post(
            VALIDATE_API_PATH,
            json={
                "request_id": request_id,
                "input": "my phone is 999999",
                "validators": [],
            },
        )

    assert response.status_code == 200

    body = response.json()
    assert body["success"] is False
    assert SAFE_TEXT_FIELD not in body["data"]
    assert body["error"]


def test_guardrails_internal_error(client, mock_crud):
    with patch(build_guard_path, side_effect=Exception("Invalid validator config")):
        response = client.post(
            VALIDATE_API_PATH,
            json={
                "request_id": request_id,
                "input": "text",
                "validators": [],
            },
        )

    assert response.status_code == 200

    body = response.json()
    assert body["success"] is False
    assert SAFE_TEXT_FIELD not in body["data"]
    assert "Invalid validator config" in body["error"]
