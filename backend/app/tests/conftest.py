import os
from unittest.mock import MagicMock
# Set environment before importing ANYTHING else
os.environ["ENVIRONMENT"] = "testing"

import pytest
from fastapi.testclient import TestClient

from app.api.deps import SessionDep, verify_bearer_token
from app.api.routes import guardrails
from app.main import app

@pytest.fixture(scope="function", autouse=True)
def override_dependencies():
    """
    Override ALL external dependencies:
    - Auth
    - DB session
    - RequestLogCrud
    """

    # ---- Auth override ----
    app.dependency_overrides[verify_bearer_token] = lambda: True

    # ---- DB session override ----
    mock_session = MagicMock()
    app.dependency_overrides[SessionDep] = lambda: mock_session

    # ---- CRUD override ----
    mock_crud = MagicMock()
    mock_crud.create.return_value = MagicMock(id=1)
    mock_crud.update_success.return_value = None
    mock_crud.update_error.return_value = None

    guardrails.RequestLogCrud = lambda session: mock_crud

    yield

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="function")
def integration_client():
    # Same app, just semantic distinction
    with TestClient(app) as c:
        yield c
