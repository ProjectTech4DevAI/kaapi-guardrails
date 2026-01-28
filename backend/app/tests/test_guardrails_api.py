from unittest.mock import MagicMock, patch

import pytest

from app.tests.guardrails_mocks import MockFailure, MockResult

build_guard_path = "app.api.routes.guardrails.build_guard"
crud_path = "app.api.routes.guardrails.RequestLogCrud"

request_id = "123e4567-e89b-12d3-a456-426614174000"


@pytest.fixture
def mock_crud():
    with patch(crud_path) as mock:
        instance = mock.return_value
        instance.create.return_value = MagicMock(id=1)
        yield instance


def test_routes_exist(client):
    paths = {route.path for route in client.app.routes}
    assert "/api/v1/guardrails/input/" in paths
    assert "/api/v1/guardrails/output/" in paths


def test_input_guardrails_success(client, mock_crud):
    class MockGuard:
        def validate(self, data):
            return MockResult(validated_output="clean text")

    with patch(build_guard_path, return_value=MockGuard()):
        response = client.post(
            "/api/v1/guardrails/input/",
            json={
                "request_id": request_id,
                "input": "hello world",
                "validators": [],
            },
        )

    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    assert body["data"]["safe_input"] == "clean text"
    assert "response_id" in body["data"]


def test_input_guardrails_validation_failure(client, mock_crud):
    class MockGuard:
        def validate(self, data):
            return MockResult(
                validated_output=None,
                failures=[MockFailure("PII detected")],
            )

    with patch(build_guard_path, return_value=MockGuard()):
        response = client.post(
            "/api/v1/guardrails/input/",
            json={
                "request_id": request_id,
                "input": "my phone is 999999",
                "validators": [],
            },
        )

    assert response.status_code == 200

    body = response.json()
    assert body["success"] is False
    assert body["data"]["safe_input"] is None
    assert body["error"] == "PII detected"


def test_output_guardrails_success(client, mock_crud):
    class MockGuard:
        def validate(self, data):
            return MockResult(validated_output="safe output")

    with patch(build_guard_path, return_value=MockGuard()):
        response = client.post(
            "/api/v1/guardrails/output",
            json={
                "request_id": request_id,
                "output": "LLM output text",
                "validators": [],
            },
        )

    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    assert body["data"]["safe_output"] == "safe output"


def test_guardrails_internal_error(client, mock_crud):
    with patch(build_guard_path, side_effect=Exception("Invalid validator config")):
        response = client.post(
            "/api/v1/guardrails/input/",
            json={
                "request_id": request_id,
                "input": "text",
                "validators": [],
            },
        )

    assert response.status_code == 200

    body = response.json()
    assert body["success"] is False
    assert body["data"]["safe_input"] is None
    assert "Invalid validator config" in body["error"]