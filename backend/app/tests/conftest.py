# conftest.py
import os

os.environ["ENVIRONMENT"] = "testing"

import pytest
from fastapi import Header
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, SQLModel

from app.main import app
from app.api.deps import (
    SessionDep,
    TenantContext,
    verify_caller,
)
from app.core.config import settings
from app.core.enum import GuardrailOnFail, Stage, ValidatorType
from app.models.config.ban_list import BanList
from app.models.config.validator_config import ValidatorConfig
from app.tests.seed_data import (
    BAN_LIST_INTEGRATION_ORGANIZATION_ID,
    BAN_LIST_INTEGRATION_PROJECT_ID,
    BAN_LIST_PAYLOADS,
    VALIDATOR_INTEGRATION_ORGANIZATION_ID,
    VALIDATOR_INTEGRATION_PROJECT_ID,
    VALIDATOR_PAYLOADS,
)
from app.utils import split_validator_payload

test_engine = create_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
    echo=False,
    pool_pre_ping=True,
)


def override_session():
    with Session(test_engine) as session:
        yield session


def seed_test_data(session: Session) -> None:
    for payload in BAN_LIST_PAYLOADS.values():
        session.add(
            BanList(
                **payload,
                organization_id=BAN_LIST_INTEGRATION_ORGANIZATION_ID,
                project_id=BAN_LIST_INTEGRATION_PROJECT_ID,
            )
        )

    for payload in VALIDATOR_PAYLOADS.values():
        model_fields, config_fields = split_validator_payload(payload)
        session.add(
            ValidatorConfig(
                organization_id=VALIDATOR_INTEGRATION_ORGANIZATION_ID,
                project_id=VALIDATOR_INTEGRATION_PROJECT_ID,
                name=model_fields["name"],
                type=ValidatorType(model_fields["type"]),
                stage=Stage(model_fields["stage"]),
                on_fail_action=GuardrailOnFail(model_fields["on_fail_action"]),
                is_enabled=model_fields.get("is_enabled", True),
                config=config_fields,
            )
        )


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
    """
    Stands in for token + IP verification, but keeps tenant resolution honest:
    the scope still comes from the X-ORGANIZATION-ID / X-PROJECT-ID headers, so
    multi-tenant isolation tests exercise the real header contract. Tests that
    don't care about tenancy send no headers and get the default scope.
    """

    def override_verify_caller(
        organization_id: int | None = Header(default=None, alias="X-ORGANIZATION-ID"),
        project_id: int | None = Header(default=None, alias="X-PROJECT-ID"),
    ):
        if organization_id is None or project_id is None:
            return TenantContext(
                organization_id=BAN_LIST_INTEGRATION_ORGANIZATION_ID,
                project_id=BAN_LIST_INTEGRATION_PROJECT_ID,
            )
        return TenantContext(
            organization_id=organization_id, project_id=project_id
        )

    app.dependency_overrides[verify_caller] = override_verify_caller

    app.dependency_overrides[SessionDep] = override_session

    yield

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def seed_db():
    with Session(test_engine) as session:
        seed_test_data(session)
        session.commit()
        yield


@pytest.fixture
def clear_database():
    """Compatibility fixture; database cleanup is handled by clean_db."""
    yield


@pytest.fixture(scope="function")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="function")
def integration_client(client):
    yield client
