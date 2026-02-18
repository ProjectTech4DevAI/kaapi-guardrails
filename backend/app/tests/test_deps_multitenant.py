from unittest.mock import Mock

import httpx
import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api.deps import TenantContext, validate_multitenant_key
from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers

BASE_AUTH_URL = "http://kaapi.local/api/v1"
VERIFY_URL = f"{BASE_AUTH_URL}/apikeys/verify"


def test_validate_multitenant_key_parses_credentials_shape(monkeypatch):
    monkeypatch.setattr(
        settings,
        "KAAPI_AUTH_URL",
        BASE_AUTH_URL,
    )

    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "success": True,
        "data": {"organization_id": 10, "project_id": 20},
    }

    captured = {}

    def fake_get(url, headers, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        return response

    monkeypatch.setattr(httpx, "get", fake_get)

    context = validate_multitenant_key("ApiKey abc123")

    assert isinstance(context, TenantContext)
    assert (context.organization_id, context.project_id) == (10, 20)
    assert captured["url"] == VERIFY_URL
    assert captured["headers"]["X-API-KEY"] == "ApiKey abc123"
    assert captured["timeout"] == 5


def test_validate_multitenant_key_invalid_status_returns_401(monkeypatch):
    monkeypatch.setattr(
        settings,
        "KAAPI_AUTH_URL",
        BASE_AUTH_URL,
    )

    response = Mock()
    response.status_code = 401
    response.json.return_value = {"success": False, "data": None}

    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: response)

    with pytest.raises(HTTPException) as exc:
        validate_multitenant_key("abc123")

    assert exc.value.status_code == 401


def test_validate_multitenant_key_network_error_returns_503(monkeypatch):
    monkeypatch.setattr(
        settings,
        "KAAPI_AUTH_URL",
        BASE_AUTH_URL,
    )

    def fake_get(*args, **kwargs):
        raise httpx.RequestError("boom", request=Mock())

    monkeypatch.setattr(httpx, "get", fake_get)

    with pytest.raises(HTTPException) as exc:
        validate_multitenant_key("abc123")

    assert exc.value.status_code == 503


def test_validate_multitenant_key_invalid_payload_returns_401(monkeypatch):
    monkeypatch.setattr(
        settings,
        "KAAPI_AUTH_URL",
        BASE_AUTH_URL,
    )

    response = Mock()
    response.status_code = 200
    response.json.return_value = {"success": True, "data": {"foo": 1}}

    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: response)

    with pytest.raises(HTTPException) as exc:
        validate_multitenant_key("abc123")

    assert exc.value.status_code == 401


def test_validate_multitenant_key_rejects_empty_header():
    with pytest.raises(HTTPException) as exc:
        validate_multitenant_key("   ")

    assert exc.value.status_code == 401


def test_validate_multitenant_key_accepts_raw_header_value(monkeypatch):
    monkeypatch.setattr(
        settings,
        "KAAPI_AUTH_URL",
        "http://localhost:8000/api/v1",
    )

    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "success": True,
        "data": {"organization_id": 1, "project_id": 1},
    }

    captured = {}

    def fake_get(url, headers, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        return response

    monkeypatch.setattr(httpx, "get", fake_get)

    context = validate_multitenant_key("ApiKey No3x47A5")

    assert isinstance(context, TenantContext)
    assert context.organization_id == 1
    assert context.project_id == 1
    assert captured["url"] == "http://localhost:8000/api/v1/apikeys/verify"
    assert captured["headers"]["X-API-KEY"] == "ApiKey No3x47A5"
    assert captured["timeout"] == 5


def test_validate_multitenant_key_malformed_json_returns_500_at_api_level(monkeypatch):
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/tenant")
    def tenant_route(_: TenantContext = Depends(validate_multitenant_key)):
        return {"ok": True}

    monkeypatch.setattr(
        settings,
        "KAAPI_AUTH_URL",
        "http://localhost:8000/api/v1",
    )

    response = Mock()
    response.status_code = 200
    response.json.side_effect = ValueError("Malformed JSON")

    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: response)

    with TestClient(app, raise_server_exceptions=False) as client:
        result = client.get("/tenant", headers={"X-API-KEY": "abc123"})

    assert result.status_code == 500
    body = result.json()
    assert body["success"] is False
    assert body["error"] == "Malformed JSON"
