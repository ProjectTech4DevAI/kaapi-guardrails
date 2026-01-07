import pytest

from unittest.mock import patch
from app.core.guardrail_controller import build_guard
from app.api.routes.guardrails import _validate_with_guard

class MockResult:
    def __init__(self, validated_output=None, failures=None):
        self.validated_output = validated_output
        self.failures = failures

class MockFailure:
    def __init__(self, msg):
        self.failure_message = msg

build_guard_path = "app.api.routes.guardrails.build_guard"

def test_routes_exist(client):
    paths = {route.path for route in client.app.routes}
    assert "/api/v1/guardrails/input/" in paths
    assert "/api/v1/guardrails/output" in paths

def test_input_guardrails_success(client):
    class MockGuard:
        def validate(self, data):
            return MockResult(validated_output="clean text")

    with patch(
        build_guard_path,
        return_value=MockGuard(),
    ):
        response = client.post(
            "/api/v1/guardrails/input/",
            json={
                "input": "hello world",
                "validators": [],
            },
        )

    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    assert body["data"]["safe_input"] == "clean text"
    assert "response_id" in body["data"]

def test_input_guardrails_validation_failure(client):
    class MockGuard:
        def validate(self, data):
            return MockResult(
                validated_output=None,
                failures=[MockFailure("PII detected")]
            )

    with patch(
        build_guard_path,
        return_value=MockGuard(),
    ):
        response = client.post(
            "/api/v1/guardrails/input/",
            json={
                "input": "my phone is 999999",
                "validators": [],
            },
        )

    assert response.status_code == 400

    body = response.json()
    assert body["success"] is False
    assert body["error"]["type"] == "validation_error"
    assert body["error"]["action"] == "reask"
    assert "PII detected" in body["error"]["failures"]

def test_output_guardrails_success(client):
    class MockGuard:
        def validate(self, data):
            return MockResult(validated_output="safe output")

    with patch(
        build_guard_path,
        return_value=MockGuard(),
    ):
        response = client.post(
            "/api/v1/guardrails/output",
            json={
                "output": "LLM output text",
                "validators": [],
            },
        )

    assert response.status_code == 200

    body = response.json()
    assert body["data"]["safe_output"] == "safe output"

def test_guardrails_internal_error(client):
    with patch(
        build_guard_path,
        side_effect=Exception("Invalid validator config"),
    ):
        response = client.post(
            "/api/v1/guardrails/input/",
            json={
                "input": "text",
                "validators": [],
            },
        )

    assert response.status_code == 500

    body = response.json()
    assert body["success"] is False
    assert body["error"]["type"] == "config_error"
    assert "Invalid validator config" in body["error"]["reason"]

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
        )

    assert response.status_code == 500

    body = response.body.decode()
    assert "config_error" in body
    assert "Invalid config" in body
