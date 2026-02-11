import uuid
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import Session

from app.api.routes.banlist_configs import (
    create_banlist,
    list_banlists,
    get_banlist,
    update_banlist,
    delete_banlist,
)
from app.schemas.banlist import BanListUpdate
from app.tests.seed_data import (
    BANLIST_TEST_ID,
    BANLIST_TEST_ORGANIZATION_ID,
    BANLIST_TEST_PROJECT_ID,
    build_banlist_create_payload,
    build_sample_banlist_mock,
)


@pytest.fixture
def mock_session():
    return MagicMock(spec=Session)


@pytest.fixture
def sample_banlist():
    return build_sample_banlist_mock()


@pytest.fixture
def create_payload():
    return build_banlist_create_payload()


def test_create_calls_crud(mock_session, create_payload, sample_banlist):
    with patch("app.api.routes.banlist_configs.banlist_crud") as crud:
        crud.create.return_value = sample_banlist

        result = create_banlist(
            payload=create_payload,
            session=mock_session,
            organization_id=BANLIST_TEST_ORGANIZATION_ID,
            project_id=BANLIST_TEST_PROJECT_ID,
            _=None,
        )

        assert result.data == sample_banlist


def test_list_returns_data(mock_session, sample_banlist):
    with patch("app.api.routes.banlist_configs.banlist_crud") as crud:
        crud.list.return_value = [sample_banlist]

        result = list_banlists(
            organization_id=BANLIST_TEST_ORGANIZATION_ID,
            project_id=BANLIST_TEST_PROJECT_ID,
            session=mock_session,
            _=None,
        )

        assert len(result.data) == 1


def test_get_success(mock_session, sample_banlist):
    with patch("app.api.routes.banlist_configs.banlist_crud") as crud:
        crud.get.return_value = sample_banlist

        result = get_banlist(
            id=BANLIST_TEST_ID,
            organization_id=BANLIST_TEST_ORGANIZATION_ID,
            project_id=BANLIST_TEST_PROJECT_ID,
            session=mock_session,
            _=None,
        )

        assert result.data == sample_banlist


def test_update_success(mock_session, sample_banlist):
    with patch("app.api.routes.banlist_configs.banlist_crud") as crud:
        crud.get.return_value = sample_banlist
        crud.update.return_value = sample_banlist

        result = update_banlist(
            id=BANLIST_TEST_ID,
            organization_id=BANLIST_TEST_ORGANIZATION_ID,
            project_id=BANLIST_TEST_PROJECT_ID,
            payload=BanListUpdate(name="new"),
            session=mock_session,
            _=None,
        )

        assert result.data == sample_banlist


def test_delete_success(mock_session, sample_banlist):
    with patch("app.api.routes.banlist_configs.banlist_crud") as crud:
        crud.get.return_value = sample_banlist

        result = delete_banlist(
            id=BANLIST_TEST_ID,
            organization_id=BANLIST_TEST_ORGANIZATION_ID,
            project_id=BANLIST_TEST_PROJECT_ID,
            session=mock_session,
            _=None,
        )

        assert result.success is True
