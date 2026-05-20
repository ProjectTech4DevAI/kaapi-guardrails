from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from sqlmodel import Session

from app.api.deps import TenantContext
from app.api.routes.llm_prompt_configs import (
    create_llm_prompt_config,
    delete_llm_prompt_config,
    get_llm_prompt_config,
    list_llm_prompt_configs,
    update_llm_prompt_config,
)
from app.core.enum import LLMValidatorName
from app.schemas.llm_prompt_config import LLMPromptConfigCreate, LLMPromptConfigUpdate

TEST_ID = UUID("223e4567-e89b-12d3-a456-426614174111")
TEST_ORG_ID = 101
TEST_PROJECT_ID = 202

TOPIC_PROMPT = "Pregnancy care: Questions related to prenatal care and supplements."
ANSWER_PROMPT = "Query: {query}\nAnswer: {answer}\nRelevant? YES or NO."


@pytest.fixture
def mock_session():
    return MagicMock(spec=Session)


@pytest.fixture
def sample_topic_config():
    obj = MagicMock()
    obj.id = TEST_ID
    obj.validator_name = LLMValidatorName.TopicRelevance
    obj.name = "Maternal Health Scope"
    obj.description = "Topic scope for maternal health bot"
    obj.prompt_schema_version = 1
    obj.llm_prompt = TOPIC_PROMPT
    obj.is_active = True
    obj.organization_id = TEST_ORG_ID
    obj.project_id = TEST_PROJECT_ID
    return obj


@pytest.fixture
def sample_answer_config():
    obj = MagicMock()
    obj.id = TEST_ID
    obj.validator_name = LLMValidatorName.AnswerRelevanceCustomLLM
    obj.name = "Health Relevance"
    obj.description = "Checks answer relevance for health queries"
    obj.prompt_schema_version = 1
    obj.llm_prompt = ANSWER_PROMPT
    obj.is_active = True
    obj.organization_id = TEST_ORG_ID
    obj.project_id = TEST_PROJECT_ID
    return obj


@pytest.fixture
def topic_create_payload():
    return LLMPromptConfigCreate(
        validator_name=LLMValidatorName.TopicRelevance,
        name="Maternal Health Scope",
        description="Topic scope for maternal health bot",
        prompt_schema_version=1,
        llm_prompt=TOPIC_PROMPT,
    )


@pytest.fixture
def answer_create_payload():
    return LLMPromptConfigCreate(
        validator_name=LLMValidatorName.AnswerRelevanceCustomLLM,
        name="Health Relevance",
        description="Checks answer relevance for health queries",
        llm_prompt=ANSWER_PROMPT,
    )


@pytest.fixture
def auth_context():
    return TenantContext(
        organization_id=TEST_ORG_ID,
        project_id=TEST_PROJECT_ID,
    )


def test_create_topic_relevance_config(
    mock_session, topic_create_payload, sample_topic_config, auth_context
):
    with patch("app.api.routes.llm_prompt_configs.llm_prompt_config_crud") as crud:
        crud.create.return_value = sample_topic_config

        result = create_llm_prompt_config(
            payload=topic_create_payload,
            session=mock_session,
            auth=auth_context,
        )

        crud.create.assert_called_once_with(
            mock_session,
            topic_create_payload,
            TEST_ORG_ID,
            TEST_PROJECT_ID,
        )
        assert result.data == sample_topic_config


def test_create_answer_relevance_config(
    mock_session, answer_create_payload, sample_answer_config, auth_context
):
    with patch("app.api.routes.llm_prompt_configs.llm_prompt_config_crud") as crud:
        crud.create.return_value = sample_answer_config

        result = create_llm_prompt_config(
            payload=answer_create_payload,
            session=mock_session,
            auth=auth_context,
        )

        assert result.data == sample_answer_config


def test_list_all_configs(
    mock_session, sample_topic_config, sample_answer_config, auth_context
):
    with patch("app.api.routes.llm_prompt_configs.llm_prompt_config_crud") as crud:
        crud.list.return_value = [sample_topic_config, sample_answer_config]

        result = list_llm_prompt_configs(
            session=mock_session,
            auth=auth_context,
        )

        crud.list.assert_called_once_with(
            mock_session,
            TEST_ORG_ID,
            TEST_PROJECT_ID,
            validator_name=None,
            offset=0,
            limit=None,
        )
        assert len(result.data) == 2


def test_list_filtered_by_validator_name(
    mock_session, sample_topic_config, auth_context
):
    with patch("app.api.routes.llm_prompt_configs.llm_prompt_config_crud") as crud:
        crud.list.return_value = [sample_topic_config]

        result = list_llm_prompt_configs(
            session=mock_session,
            auth=auth_context,
            validator_name=LLMValidatorName.TopicRelevance,
        )

        crud.list.assert_called_once_with(
            mock_session,
            TEST_ORG_ID,
            TEST_PROJECT_ID,
            validator_name=LLMValidatorName.TopicRelevance,
            offset=0,
            limit=None,
        )
        assert len(result.data) == 1


def test_get_success(mock_session, sample_topic_config, auth_context):
    with patch("app.api.routes.llm_prompt_configs.llm_prompt_config_crud") as crud:
        crud.get.return_value = sample_topic_config

        result = get_llm_prompt_config(
            id=TEST_ID,
            session=mock_session,
            auth=auth_context,
        )

        crud.get.assert_called_once_with(
            mock_session, TEST_ID, TEST_ORG_ID, TEST_PROJECT_ID
        )
        assert result.data == sample_topic_config


def test_update_success(mock_session, sample_topic_config, auth_context):
    with patch("app.api.routes.llm_prompt_configs.llm_prompt_config_crud") as crud:
        crud.update.return_value = sample_topic_config

        result = update_llm_prompt_config(
            id=TEST_ID,
            payload=LLMPromptConfigUpdate(name="updated"),
            session=mock_session,
            auth=auth_context,
        )

        crud.update.assert_called_once()
        args, _ = crud.update.call_args
        assert args[1] == TEST_ID
        assert args[2] == TEST_ORG_ID
        assert args[3] == TEST_PROJECT_ID
        assert args[4].name == "updated"
        assert result.data == sample_topic_config


def test_delete_success(mock_session, sample_topic_config, auth_context):
    with patch("app.api.routes.llm_prompt_configs.llm_prompt_config_crud") as crud:
        crud.get.return_value = sample_topic_config

        result = delete_llm_prompt_config(
            id=TEST_ID,
            session=mock_session,
            auth=auth_context,
        )

        crud.get.assert_called_once_with(
            mock_session, TEST_ID, TEST_ORG_ID, TEST_PROJECT_ID
        )
        crud.delete.assert_called_once_with(mock_session, sample_topic_config)
        assert result.success is True
