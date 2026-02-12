from unittest.mock import MagicMock, patch

import pytest

from app.core.enum import GuardrailOnFail
from app.schemas.guardrail_config import GuardrailRequest
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


def test_guardrail_request_normalizes_validator_config_payload():
    payload = {
        "request_id": request_id,
        "input": "hello world",
        "validators": [
            {
                "type": "uli_slur_match",
                "stage": "input",
                "on_fail_action": "fix",
                "is_enabled": True,
                "id": "55ddfc03-1b70-453b-80c8-a1de449a02ee",
                "config_id": "15c0f5bc-5e6c-412c-979b-f9b988334d1e",
                "created_at": "2026-02-12T14:50:30.936285",
                "updated_at": "2026-02-12T14:50:30.936294",
                "organization_id": 1,
                "project_id": 1,
                "severity": "high",
            }
        ],
    }

    request = GuardrailRequest.model_validate(payload)
    validator = request.validators[0]
    validator_dump = validator.model_dump()

    assert validator_dump["type"] == "uli_slur_match"
    assert validator_dump["on_fail"] == GuardrailOnFail.Fix
    assert validator_dump["severity"] == "high"
    assert "config_id" not in validator_dump
    assert "id" not in validator_dump
    assert "organization_id" not in validator_dump
    assert "project_id" not in validator_dump


def test_guardrail_request_preserves_on_fail_when_present():
    payload = {
        "request_id": request_id,
        "input": "hello world",
        "validators": [
            {
                "type": "pii_remover",
                "on_fail": "rephrase",
                "on_fail_action": "fix",
            }
        ],
    }

    request = GuardrailRequest.model_validate(payload)
    validator_dump = request.validators[0].model_dump()

    assert validator_dump["type"] == "pii_remover"
    assert validator_dump["on_fail"] == GuardrailOnFail.Rephrase
