import uuid
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import Session

from app.api.deps import TenantContext
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


@pytest.fixture
def auth_context():
    return TenantContext(
        organization_id=BAN_LIST_TEST_ORGANIZATION_ID,
        project_id=BAN_LIST_TEST_PROJECT_ID,
    )


def test_create_calls_crud(mock_session, create_payload, sample_ban_list, auth_context):
    with patch("app.api.routes.ban_list_configs.ban_list_crud") as crud:
        crud.create.return_value = sample_ban_list

        result = create_ban_list(
            payload=create_payload,
            session=mock_session,
            auth=auth_context,
        )

        assert result.data == sample_ban_list


def test_list_returns_data(mock_session, sample_ban_list, auth_context):
    with patch("app.api.routes.ban_list_configs.ban_list_crud") as crud:
        crud.list.return_value = [sample_ban_list]

        result = list_ban_lists(
            session=mock_session,
            auth=auth_context,
        )

        assert len(result.data) == 1


def test_get_success(mock_session, sample_ban_list, auth_context):
    with patch("app.api.routes.ban_list_configs.ban_list_crud") as crud:
        crud.get.return_value = sample_ban_list

        result = get_ban_list(
            id=BAN_LIST_TEST_ID,
            session=mock_session,
            auth=auth_context,
        )

        assert result.data == sample_ban_list


def test_update_success(mock_session, sample_ban_list, auth_context):
    with patch("app.api.routes.ban_list_configs.ban_list_crud") as crud:
        crud.update.return_value = sample_ban_list

        result = update_ban_list(
            id=BAN_LIST_TEST_ID,
            payload=BanListUpdate(name="new"),
            session=mock_session,
            auth=auth_context,
        )

        crud.update.assert_called_once()
        _, kwargs = crud.update.call_args
        assert kwargs["id"] == BAN_LIST_TEST_ID
        assert kwargs["organization_id"] == BAN_LIST_TEST_ORGANIZATION_ID
        assert kwargs["project_id"] == BAN_LIST_TEST_PROJECT_ID
        assert kwargs["data"].name == "new"
        assert result.data == sample_ban_list


def test_delete_success(mock_session, sample_ban_list, auth_context):
    with patch("app.api.routes.ban_list_configs.ban_list_crud") as crud:
        crud.get.return_value = sample_ban_list

        result = delete_ban_list(
            id=BAN_LIST_TEST_ID,
            session=mock_session,
            auth=auth_context,
        )

        crud.get.assert_called_once_with(
            mock_session,
            BAN_LIST_TEST_ID,
            BAN_LIST_TEST_ORGANIZATION_ID,
            BAN_LIST_TEST_PROJECT_ID,
            require_owner=True,
        )
        crud.delete.assert_called_once_with(mock_session, sample_ban_list)
        assert result.success is True
