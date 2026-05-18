from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from sqlmodel import Session

from app.api.deps import TenantContext
from app.api.routes.answer_relevance_prompts import (
    create_answer_relevance_prompt,
    delete_answer_relevance_prompt,
    get_answer_relevance_prompt,
    list_answer_relevance_prompts,
    update_answer_relevance_prompt,
)
from app.schemas.answer_relevance_prompt import (
    AnswerRelevancePromptCreate,
    AnswerRelevancePromptUpdate,
)

PROMPT_TEST_ID = UUID("aaaabbbb-cccc-dddd-eeee-ffffffffffff")
PROMPT_TEST_ORG_ID = 5
PROMPT_TEST_PROJECT_ID = 50
VALID_TEMPLATE = "Query: {query}\nAnswer: {answer}\nRelevant? YES or NO."


@pytest.fixture
def mock_session():
    return MagicMock(spec=Session)


@pytest.fixture
def sample_prompt():
    obj = MagicMock()
    obj.id = PROMPT_TEST_ID
    obj.name = "Health Relevance"
    obj.description = "Checks answer relevance for health queries"
    obj.prompt_template = VALID_TEMPLATE
    obj.is_active = True
    obj.organization_id = PROMPT_TEST_ORG_ID
    obj.project_id = PROMPT_TEST_PROJECT_ID
    return obj


@pytest.fixture
def create_payload():
    return AnswerRelevancePromptCreate(
        name="Health Relevance",
        description="Checks answer relevance for health queries",
        prompt_template=VALID_TEMPLATE,
    )


@pytest.fixture
def auth_context():
    return TenantContext(
        organization_id=PROMPT_TEST_ORG_ID,
        project_id=PROMPT_TEST_PROJECT_ID,
    )


def test_create_calls_crud(mock_session, create_payload, sample_prompt, auth_context):
    with patch(
        "app.api.routes.answer_relevance_prompts.answer_relevance_prompt_crud"
    ) as crud:
        crud.create.return_value = sample_prompt

        result = create_answer_relevance_prompt(
            payload=create_payload,
            session=mock_session,
            auth=auth_context,
        )

        crud.create.assert_called_once_with(
            mock_session,
            create_payload,
            PROMPT_TEST_ORG_ID,
            PROMPT_TEST_PROJECT_ID,
        )
        assert result.data == sample_prompt


def test_list_returns_data(mock_session, sample_prompt, auth_context):
    with patch(
        "app.api.routes.answer_relevance_prompts.answer_relevance_prompt_crud"
    ) as crud:
        crud.list.return_value = [sample_prompt]

        result = list_answer_relevance_prompts(
            session=mock_session,
            auth=auth_context,
        )

        crud.list.assert_called_once_with(
            mock_session,
            PROMPT_TEST_ORG_ID,
            PROMPT_TEST_PROJECT_ID,
            0,
            None,
        )
        assert len(result.data) == 1


def test_get_success(mock_session, sample_prompt, auth_context):
    with patch(
        "app.api.routes.answer_relevance_prompts.answer_relevance_prompt_crud"
    ) as crud:
        crud.get.return_value = sample_prompt

        result = get_answer_relevance_prompt(
            id=PROMPT_TEST_ID,
            session=mock_session,
            auth=auth_context,
        )

        crud.get.assert_called_once_with(
            mock_session,
            PROMPT_TEST_ID,
            PROMPT_TEST_ORG_ID,
            PROMPT_TEST_PROJECT_ID,
        )
        assert result.data == sample_prompt


def test_update_success(mock_session, sample_prompt, auth_context):
    with patch(
        "app.api.routes.answer_relevance_prompts.answer_relevance_prompt_crud"
    ) as crud:
        crud.update.return_value = sample_prompt

        result = update_answer_relevance_prompt(
            id=PROMPT_TEST_ID,
            payload=AnswerRelevancePromptUpdate(name="updated"),
            session=mock_session,
            auth=auth_context,
        )

        crud.update.assert_called_once()
        args, _ = crud.update.call_args
        assert args[0] == mock_session
        assert args[1] == PROMPT_TEST_ID
        assert args[2] == PROMPT_TEST_ORG_ID
        assert args[3] == PROMPT_TEST_PROJECT_ID
        assert result.data == sample_prompt


def test_delete_success(mock_session, sample_prompt, auth_context):
    with patch(
        "app.api.routes.answer_relevance_prompts.answer_relevance_prompt_crud"
    ) as crud:
        crud.get.return_value = sample_prompt

        result = delete_answer_relevance_prompt(
            id=PROMPT_TEST_ID,
            session=mock_session,
            auth=auth_context,
        )

        crud.get.assert_called_once_with(
            mock_session,
            PROMPT_TEST_ID,
            PROMPT_TEST_ORG_ID,
            PROMPT_TEST_PROJECT_ID,
        )
        crud.delete.assert_called_once_with(mock_session, sample_prompt)
        assert result.success is True
