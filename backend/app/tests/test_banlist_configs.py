import uuid
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import Session

from app.api.routes.ban_list_configs import (
    create_ban_list,
    list_ban_lists,
    get_ban_list,
    update_ban_list,
    delete_ban_list,
)
from app.schemas.ban_list import BanListUpdate
from app.tests.seed_data import (
    BAN_LIST_TEST_ID,
    BAN_LIST_TEST_ORGANIZATION_ID,
    BAN_LIST_TEST_PROJECT_ID,
    build_ban_list_create_payload,
    build_sample_ban_list_mock,
)


@pytest.fixture
def mock_session():
    return MagicMock(spec=Session)


@pytest.fixture
def sample_ban_list():
    return build_sample_ban_list_mock()


@pytest.fixture
def create_payload():
    return build_ban_list_create_payload()


def test_create_calls_crud(mock_session, create_payload, sample_ban_list):
    with patch("app.api.routes.ban_list_configs.ban_list_crud") as crud:
        crud.create.return_value = sample_ban_list

        result = create_ban_list(
            payload=create_payload,
            session=mock_session,
            organization_id=BAN_LIST_TEST_ORGANIZATION_ID,
            project_id=BAN_LIST_TEST_PROJECT_ID,
            _=None,
        )

        assert result.data == sample_ban_list


def test_list_returns_data(mock_session, sample_ban_list):
    with patch("app.api.routes.ban_list_configs.ban_list_crud") as crud:
        crud.list.return_value = [sample_ban_list]

        result = list_ban_lists(
            organization_id=BAN_LIST_TEST_ORGANIZATION_ID,
            project_id=BAN_LIST_TEST_PROJECT_ID,
            session=mock_session,
            _=None,
        )

        assert len(result.data) == 1


def test_get_success(mock_session, sample_ban_list):
    with patch("app.api.routes.ban_list_configs.ban_list_crud") as crud:
        crud.get.return_value = sample_ban_list

        result = get_ban_list(
            id=BAN_LIST_TEST_ID,
            organization_id=BAN_LIST_TEST_ORGANIZATION_ID,
            project_id=BAN_LIST_TEST_PROJECT_ID,
            session=mock_session,
            _=None,
        )

        assert result.data == sample_ban_list


def test_update_success(mock_session, sample_ban_list):
    with patch("app.api.routes.ban_list_configs.ban_list_crud") as crud:
        crud.get.return_value = sample_ban_list
        crud.update.return_value = sample_ban_list

        result = update_ban_list(
            id=BAN_LIST_TEST_ID,
            organization_id=BAN_LIST_TEST_ORGANIZATION_ID,
            project_id=BAN_LIST_TEST_PROJECT_ID,
            payload=BanListUpdate(name="new"),
            session=mock_session,
            _=None,
        )

        assert result.data == sample_ban_list


def test_delete_success(mock_session, sample_ban_list):
    with patch("app.api.routes.ban_list_configs.ban_list_crud") as crud:
        crud.get.return_value = sample_ban_list

        result = delete_ban_list(
            id=BAN_LIST_TEST_ID,
            organization_id=BAN_LIST_TEST_ORGANIZATION_ID,
            project_id=BAN_LIST_TEST_PROJECT_ID,
            session=mock_session,
            _=None,
        )

        assert result.success is True
