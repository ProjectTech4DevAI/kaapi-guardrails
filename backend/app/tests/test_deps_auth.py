import hashlib

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import AuthDep, TenantContext
from app.core.config import settings

TOKEN = "test-token"
TOKEN_HASH = hashlib.sha256(TOKEN.encode()).hexdigest()

TENANT_HEADERS = {"X-ORGANIZATION-ID": "7", "X-PROJECT-ID": "9"}
AUTH_HEADERS = {"Authorization": f"Bearer {TOKEN}", **TENANT_HEADERS}


@pytest.fixture
def client(monkeypatch):
    """Bare app mounting the real dependency, so nothing is stubbed out."""
    monkeypatch.setattr(settings, "AUTH_TOKEN", TOKEN_HASH)

    app = FastAPI()

    @app.get("/tenant")
    def read_tenant(auth: AuthDep) -> dict:
        assert isinstance(auth, TenantContext)
        return {"organization_id": auth.organization_id, "project_id": auth.project_id}

    return TestClient(app)


def test_valid_request_returns_tenant_from_headers(client):
    response = client.get("/tenant", headers=AUTH_HEADERS)

    assert response.status_code == 200
    assert response.json() == {"organization_id": 7, "project_id": 9}


def test_token_is_checked_before_tenant_header_validation(client):
    """A wrong token gets 401 before the tenant headers are even looked at."""
    response = client.get("/tenant", headers={"Authorization": "Bearer nope"})

    assert response.status_code == 401


def test_missing_token_is_unauthorized(client):
    response = client.get("/tenant", headers=TENANT_HEADERS)

    assert response.status_code == 401


def test_wrong_token_is_unauthorized(client):
    response = client.get(
        "/tenant", headers={"Authorization": "Bearer nope", **TENANT_HEADERS}
    )

    assert response.status_code == 401


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"X-ORGANIZATION-ID": "7"},
        {"X-PROJECT-ID": "9"},
        {"X-ORGANIZATION-ID": "not-an-int", "X-PROJECT-ID": "9"},
    ],
)
def test_missing_or_invalid_tenant_headers_are_rejected(client, headers):
    response = client.get(
        "/tenant", headers={"Authorization": f"Bearer {TOKEN}", **headers}
    )

    assert response.status_code == 422
