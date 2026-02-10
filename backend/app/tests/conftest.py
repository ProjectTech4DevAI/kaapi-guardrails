# conftest.py
import os

os.environ["ENVIRONMENT"] = "testing"

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, SQLModel

from app.main import app
from app.api.deps import SessionDep, verify_bearer_token
from app.core.config import settings

test_engine = create_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
    echo=False,
    pool_pre_ping=True,
)


def override_session():
    with Session(test_engine) as session:
        yield session


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    SQLModel.metadata.create_all(test_engine)
    yield
    SQLModel.metadata.drop_all(test_engine)


@pytest.fixture(scope="function", autouse=True)
def clean_db():
    with Session(test_engine) as session:
        for table in reversed(SQLModel.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()


@pytest.fixture(scope="function", autouse=True)
def override_dependencies():
    app.dependency_overrides[verify_bearer_token] = lambda: True

    app.dependency_overrides[SessionDep] = override_session

    yield

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="function")
def integration_client(client):
    yield client
