import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlmodel import Session

from app.api.routes.banlist_configs import (
    create_banlist,
    list_banlists,
    get_banlist,
    update_banlist,
    delete_banlist,
)
from app.schemas.banlist import BanListCreate, BanListUpdate


TEST_ID = uuid.uuid4()
TEST_ORGANIZATION_ID = 1
TEST_PROJECT_ID = 10


@pytest.fixture
def mock_session():
    return MagicMock(spec=Session)


@pytest.fixture
def sample_banlist():
    obj = MagicMock()
    obj.id = TEST_ID
    obj.name = "test"
    obj.description = "desc"
    obj.banned_words = ["bad"]
    obj.organization_id = TEST_ORGANIZATION_ID
    obj.project_id = TEST_PROJECT_ID
    obj.domain = "health"
    obj.is_public = False
    return obj


@pytest.fixture
def create_payload():
    return BanListCreate(
        name="test",
        description="desc",
        banned_words=["bad"],
        domain="health",
        is_public=False,
    )


def test_create_calls_crud(mock_session, create_payload, sample_banlist):
    with patch("app.api.routes.banlist_configs.banlist_crud") as crud:
        crud.create.return_value = sample_banlist

        result = create_banlist(
            payload=create_payload,
            session=mock_session,
            organization_id=TEST_ORGANIZATION_ID,
            project_id=TEST_PROJECT_ID,
            _=None,
        )

        assert result.data == sample_banlist


def test_list_returns_data(mock_session, sample_banlist):
    with patch("app.api.routes.banlist_configs.banlist_crud") as crud:
        crud.list.return_value = [sample_banlist]

        result = list_banlists(
            organization_id=TEST_ORGANIZATION_ID,
            project_id=TEST_PROJECT_ID,
            session=mock_session,
            _=None,
        )

        assert len(result.data) == 1


def test_get_success(mock_session, sample_banlist):
    with patch("app.api.routes.banlist_configs.banlist_crud") as crud:
        crud.get.return_value = sample_banlist

        result = get_banlist(
            id=TEST_ID,
            organization_id=TEST_ORGANIZATION_ID,
            project_id=TEST_PROJECT_ID,
            session=mock_session,
            _=None,
        )

        assert result.data == sample_banlist

def test_update_success(mock_session, sample_banlist):
    with patch("app.api.routes.banlist_configs.banlist_crud") as crud:
        crud.get.return_value = sample_banlist
        crud.update.return_value = sample_banlist

        result = update_banlist(
            id=TEST_ID,
            organization_id=TEST_ORGANIZATION_ID,
            project_id=TEST_PROJECT_ID,
            payload=BanListUpdate(name="new"),
            session=mock_session,
            _=None,
        )

        assert result.data == sample_banlist


def test_delete_success(mock_session, sample_banlist):
    with patch("app.api.routes.banlist_configs.banlist_crud") as crud:
        crud.get.return_value = sample_banlist

        result = delete_banlist(
            id=TEST_ID,
            organization_id=TEST_ORGANIZATION_ID,
            project_id=TEST_PROJECT_ID,
            session=mock_session,
            _=None,
        )

        assert result.success is True
