import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlmodel import Session

from app.api.routes.ban_list_configs import (
    create_ban_list,
    list_ban_lists,
    get_ban_list,
    update_ban_list,
    delete_ban_list,
)
from app.schemas.ban_list_config import (
    BanListCreate,
    BanListUpdate,
)

TEST_ID = uuid.uuid4()
TEST_ORG_ID = 1
TEST_PROJECT_ID = 10

@pytest.fixture
def mock_session():
    return MagicMock(spec=Session)


@pytest.fixture
def sample_ban_list():
    obj = MagicMock()
    obj.id = TEST_ID
    obj.name = "test"
    obj.description = "desc"
    obj.banned_words = ["bad"]
    obj.org_id = TEST_ORG_ID
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


def test_create_calls_crud(mock_session, create_payload, sample_ban_list):
    with patch("app.api.routes.ban_list_configs.ban_list_crud") as crud:
        crud.create.return_value = sample_ban_list

        result = create_ban_list(
            payload=create_payload,
            session=mock_session,
            org_id=TEST_ORG_ID,
            project_id=TEST_PROJECT_ID,
            _=None,
        )

        crud.create.assert_called_once()
        assert result == sample_ban_list


def test_list_returns_data(mock_session, sample_ban_list):
    with patch("app.api.routes.ban_list_configs.ban_list_crud") as crud:
        crud.list.return_value = [sample_ban_list]

        result = list_ban_lists(
            org_id=TEST_ORG_ID,
            project_id=TEST_PROJECT_ID,
            session=mock_session,
            _=None,
        )

        assert len(result) == 1
        crud.list.assert_called_once()


def test_get_success(mock_session, sample_ban_list):
    with patch("app.api.routes.ban_list_configs.ban_list_crud") as crud:
        crud.get.return_value = sample_ban_list

        result = get_ban_list(
            id=TEST_ID,
            org_id=TEST_ORG_ID,
            project_id=TEST_PROJECT_ID,
            session=mock_session,
            _=None,
        )

        assert result == sample_ban_list


def test_get_not_found(mock_session):
    with patch("app.api.routes.ban_list_configs.ban_list_crud") as crud:
        crud.get.return_value = None

        with pytest.raises(HTTPException) as exc:
            get_ban_list(
                id=TEST_ID,
                org_id=TEST_ORG_ID,
                project_id=TEST_PROJECT_ID,
                session=mock_session,
                _=None,
            )

        assert exc.value.status_code == 404


def test_get_forbidden(mock_session, sample_ban_list):
    sample_ban_list.org_id = 999  # different owner

    with patch("app.api.routes.ban_list_configs.ban_list_crud") as crud:
        crud.get.return_value = sample_ban_list

        with pytest.raises(HTTPException) as exc:
            get_ban_list(
                id=TEST_ID,
                org_id=TEST_ORG_ID,
                project_id=TEST_PROJECT_ID,
                session=mock_session,
                _=None,
            )

        assert exc.value.status_code == 403


def test_update_success(mock_session, sample_ban_list):
    with patch("app.api.routes.ban_list_configs.ban_list_crud") as crud:
        crud.get.return_value = sample_ban_list
        crud.update.return_value = sample_ban_list

        result = update_ban_list(
            id=TEST_ID,
            org_id=TEST_ORG_ID,
            project_id=TEST_PROJECT_ID,
            payload=BanListUpdate(name="new"),
            session=mock_session,
            _=None,
        )

        crud.update.assert_called_once()
        assert result == sample_ban_list


def test_update_forbidden(mock_session, sample_ban_list):
    sample_ban_list.org_id = 999

    with patch("app.api.routes.ban_list_configs.ban_list_crud") as crud:
        crud.get.return_value = sample_ban_list

        with pytest.raises(HTTPException) as exc:
            update_ban_list(
                id=TEST_ID,
                org_id=TEST_ORG_ID,
                project_id=TEST_PROJECT_ID,
                payload=BanListUpdate(name="new"),
                session=mock_session,
                _=None,
            )

        assert exc.value.status_code == 403


def test_delete_success(mock_session, sample_ban_list):
    with patch("app.api.routes.ban_list_configs.ban_list_crud") as crud:
        crud.get.return_value = sample_ban_list

        result = delete_ban_list(
            id=TEST_ID,
            org_id=TEST_ORG_ID,
            project_id=TEST_PROJECT_ID,
            session=mock_session,
            _=None,
        )

        crud.delete.assert_called_once()
        assert result["success"] is True


def test_delete_forbidden(mock_session, sample_ban_list):
    sample_ban_list.org_id = 999

    with patch("app.api.routes.ban_list_configs.ban_list_crud") as crud:
        crud.get.return_value = sample_ban_list

        with pytest.raises(HTTPException):
            delete_ban_list(
                id=TEST_ID,
                org_id=TEST_ORG_ID,
                project_id=TEST_PROJECT_ID,
                session=mock_session,
                _=None,
            )
