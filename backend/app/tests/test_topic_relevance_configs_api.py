from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from sqlmodel import Session

from app.api.deps import TenantContext
from app.api.routes.topic_relevance_configs import (
    create_topic_relevance_config,
    delete_topic_relevance_config,
    get_topic_relevance_config,
    list_topic_relevance_configs,
    update_topic_relevance_config,
)
from app.schemas.topic_relevance import TopicRelevanceCreate, TopicRelevanceUpdate

TOPIC_RELEVANCE_TEST_ID = UUID("223e4567-e89b-12d3-a456-426614174111")
TOPIC_RELEVANCE_TEST_ORGANIZATION_ID = 101
TOPIC_RELEVANCE_TEST_PROJECT_ID = 202


@pytest.fixture
def mock_session():
    return MagicMock(spec=Session)


@pytest.fixture
def sample_topic_relevance():
    obj = MagicMock()
    obj.id = TOPIC_RELEVANCE_TEST_ID
    obj.name = "Maternal Health Scope"
    obj.description = "Topic scope for maternal health bot"
    obj.prompt_schema_version = 1
    obj.configuration = (
        "Pregnancy care: Questions related to prenatal care and supplements."
    )
    obj.is_active = True
    obj.organization_id = TOPIC_RELEVANCE_TEST_ORGANIZATION_ID
    obj.project_id = TOPIC_RELEVANCE_TEST_PROJECT_ID
    return obj


@pytest.fixture
def create_payload():
    return TopicRelevanceCreate(
        name="Maternal Health Scope",
        description="Topic scope for maternal health bot",
        prompt_schema_version=1,
        configuration="Pregnancy care: Questions related to prenatal care and supplements.",
    )


@pytest.fixture
def auth_context():
    return TenantContext(
        organization_id=TOPIC_RELEVANCE_TEST_ORGANIZATION_ID,
        project_id=TOPIC_RELEVANCE_TEST_PROJECT_ID,
    )


def test_create_calls_crud(
    mock_session, create_payload, sample_topic_relevance, auth_context
):
    with patch("app.api.routes.topic_relevance_configs.topic_relevance_crud") as crud:
        crud.create.return_value = sample_topic_relevance

        result = create_topic_relevance_config(
            payload=create_payload,
            session=mock_session,
            auth=auth_context,
        )

        assert result.data == sample_topic_relevance


def test_list_returns_data(mock_session, sample_topic_relevance, auth_context):
    with patch("app.api.routes.topic_relevance_configs.topic_relevance_crud") as crud:
        crud.list.return_value = [sample_topic_relevance]

        result = list_topic_relevance_configs(
            session=mock_session,
            auth=auth_context,
        )

        crud.list.assert_called_once_with(
            mock_session,
            TOPIC_RELEVANCE_TEST_ORGANIZATION_ID,
            TOPIC_RELEVANCE_TEST_PROJECT_ID,
            0,
            None,
        )
        assert len(result.data) == 1


def test_get_success(mock_session, sample_topic_relevance, auth_context):
    with patch("app.api.routes.topic_relevance_configs.topic_relevance_crud") as crud:
        crud.get.return_value = sample_topic_relevance

        result = get_topic_relevance_config(
            id=TOPIC_RELEVANCE_TEST_ID,
            session=mock_session,
            auth=auth_context,
        )

        assert result.data == sample_topic_relevance


def test_update_success(mock_session, sample_topic_relevance, auth_context):
    with patch("app.api.routes.topic_relevance_configs.topic_relevance_crud") as crud:
        crud.update.return_value = sample_topic_relevance

        result = update_topic_relevance_config(
            id=TOPIC_RELEVANCE_TEST_ID,
            payload=TopicRelevanceUpdate(name="updated"),
            session=mock_session,
            auth=auth_context,
        )

        crud.update.assert_called_once()
        args, _ = crud.update.call_args
        assert args[1] == TOPIC_RELEVANCE_TEST_ID
        assert args[2] == TOPIC_RELEVANCE_TEST_ORGANIZATION_ID
        assert args[3] == TOPIC_RELEVANCE_TEST_PROJECT_ID
        assert args[4].name == "updated"
        assert result.data == sample_topic_relevance


def test_delete_success(mock_session, sample_topic_relevance, auth_context):
    with patch("app.api.routes.topic_relevance_configs.topic_relevance_crud") as crud:
        crud.get.return_value = sample_topic_relevance

        result = delete_topic_relevance_config(
            id=TOPIC_RELEVANCE_TEST_ID,
            session=mock_session,
            auth=auth_context,
        )

        crud.get.assert_called_once_with(
            mock_session,
            TOPIC_RELEVANCE_TEST_ID,
            TOPIC_RELEVANCE_TEST_ORGANIZATION_ID,
            TOPIC_RELEVANCE_TEST_PROJECT_ID,
        )
        crud.delete.assert_called_once_with(mock_session, sample_topic_relevance)
        assert result.success is True
