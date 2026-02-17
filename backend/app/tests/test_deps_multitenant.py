from unittest.mock import Mock

import httpx
import pytest
from fastapi import HTTPException

from app.api.deps import TenantContext, validate_multitenant_key
from app.core.config import settings


def test_validate_multitenant_key_parses_credentials_shape(monkeypatch):
    monkeypatch.setattr(
        settings,
        "KAAPI_BACKEND_CREDENTIAL_URL",
        "http://kaapi.local/api/v1/credentials/",
    )

    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "success": True,
        "data": [{"organization_id": 10, "project_id": 20}],
    }

    captured = {}

    def fake_get(url, headers, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        return response

    monkeypatch.setattr(httpx, "get", fake_get)

    context = validate_multitenant_key("abc123")

    assert isinstance(context, TenantContext)
    assert (context.organization_id, context.project_id) == (10, 20)
    assert captured["url"] == settings.KAAPI_BACKEND_CREDENTIAL_URL
    assert captured["headers"]["X-API-KEY"] == "ApiKey abc123"
    assert captured["timeout"] == 5


def test_validate_multitenant_key_invalid_status_returns_401(monkeypatch):
    monkeypatch.setattr(
        settings,
        "KAAPI_BACKEND_CREDENTIAL_URL",
        "http://kaapi.local/api/v1/credentials/",
    )

    response = Mock()
    response.status_code = 401
    response.json.return_value = {"success": False, "data": []}

    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: response)

    with pytest.raises(HTTPException) as exc:
        validate_multitenant_key("abc123")

    assert exc.value.status_code == 401


def test_validate_multitenant_key_network_error_returns_503(monkeypatch):
    monkeypatch.setattr(
        settings,
        "KAAPI_BACKEND_CREDENTIAL_URL",
        "http://kaapi.local/api/v1/credentials/",
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
        "KAAPI_BACKEND_CREDENTIAL_URL",
        "http://kaapi.local/api/v1/credentials/",
    )

    response = Mock()
    response.status_code = 200
    response.json.return_value = {"success": True, "data": [{"foo": 1}]}

    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: response)

    with pytest.raises(HTTPException) as exc:
        validate_multitenant_key("abc123")

    assert exc.value.status_code == 401


def test_validate_multitenant_key_rejects_empty_header():
    with pytest.raises(HTTPException) as exc:
        validate_multitenant_key("   ")

    assert exc.value.status_code == 401
