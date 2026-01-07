from collections.abc import Generator
import pytest
import os
# Set environment before importing ANYTHING else
os.environ["ENVIRONMENT"] = "testing"

from fastapi.testclient import TestClient
from sqlmodel import Session
from sqlalchemy import event

from app.core.db import engine
from app.api.deps import get_db, security
from app.main import app

@pytest.fixture(scope="function")
def client():
    from app.api.deps import verify_bearer_token

    app.dependency_overrides[verify_bearer_token] = lambda: True

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()