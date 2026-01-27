import os
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

# MUST be set before app import
os.environ["ENVIRONMENT"] = "testing"

from app.api.deps import SessionDep, verify_bearer_token
from app.api.routes import guardrails
from app.main import app

@pytest.fixture(scope="function", autouse=True)
def override_dependencies(monkeypatch):
    """
    Override ALL external dependencies:
    - Auth
    - DB session
    - CRUDs
    """

    # ---- Auth override ----
    app.dependency_overrides[verify_bearer_token] = lambda: True

    # ---- DB session override ----
    mock_session = MagicMock()
    app.dependency_overrides[SessionDep] = lambda: mock_session

    # ---- CRUD override ----
    mock_request_log_crud = MagicMock()
    mock_request_log_crud.create.return_value = MagicMock(id=1)
    mock_request_log_crud.update.return_value = None

    mock_validator_log_crud = MagicMock()
    mock_validator_log_crud.create.return_value = None

    monkeypatch.setattr(
        guardrails,
        "RequestLogCrud",
        lambda session: mock_request_log_crud,
    )
    monkeypatch.setattr(
        guardrails,
        "ValidatorLogCrud",
        lambda session: mock_validator_log_crud,
    )

    yield

    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="function")
def integration_client(client):
    yield client
