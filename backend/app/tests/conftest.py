from collections.abc import Generator
import pytest
import os
# Set environment before importing ANYTHING else
os.environ["ENVIRONMENT"] = "testing"

from fastapi.testclient import TestClient
from app.api.deps import verify_bearer_token
from app.main import app


@pytest.fixture(scope="function")
def client():
    app.dependency_overrides[verify_bearer_token] = lambda: True

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def integration_client():
    app.dependency_overrides[verify_bearer_token] = lambda: True

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()