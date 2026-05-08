from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import MultitenantAuthDep, SessionDep
from app.crud.answer_relevance_prompt import answer_relevance_prompt_crud
from app.schemas.answer_relevance_prompt import (
    AnswerRelevancePromptCreate,
    AnswerRelevancePromptResponse,
    AnswerRelevancePromptUpdate,
)
from app.utils import APIResponse, load_description

router = APIRouter(
    prefix="/guardrails/answer_relevance_prompts",
    tags=["Answer Relevance Prompts"],
)


@router.post(
    "/",
    description=load_description("answer_relevance_prompts/create_prompt.md"),
    response_model=APIResponse[AnswerRelevancePromptResponse],
)
def create_answer_relevance_prompt(
    payload: AnswerRelevancePromptCreate,
    session: SessionDep,
    auth: MultitenantAuthDep,
) -> APIResponse[AnswerRelevancePromptResponse]:
    obj = answer_relevance_prompt_crud.create(
        session, payload, auth.organization_id, auth.project_id
    )
    return APIResponse.success_response(data=obj)


@router.get(
    "/",
    description=load_description("answer_relevance_prompts/list_prompts.md"),
    response_model=APIResponse[list[AnswerRelevancePromptResponse]],
)
def list_answer_relevance_prompts(
    session: SessionDep,
    auth: MultitenantAuthDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int | None, Query(ge=1, le=100)] = None,
) -> APIResponse[list[AnswerRelevancePromptResponse]]:
    objs = answer_relevance_prompt_crud.list(
        session, auth.organization_id, auth.project_id, offset, limit
    )
    return APIResponse.success_response(data=objs)


@router.get(
    "/{id}",
    description=load_description("answer_relevance_prompts/get_prompt.md"),
    response_model=APIResponse[AnswerRelevancePromptResponse],
)
def get_answer_relevance_prompt(
    id: UUID,
    session: SessionDep,
    auth: MultitenantAuthDep,
) -> APIResponse[AnswerRelevancePromptResponse]:
    obj = answer_relevance_prompt_crud.get(
        session, id, auth.organization_id, auth.project_id
    )
    return APIResponse.success_response(data=obj)


@router.patch(
    "/{id}",
    description=load_description("answer_relevance_prompts/update_prompt.md"),
    response_model=APIResponse[AnswerRelevancePromptResponse],
)
def update_answer_relevance_prompt(
    id: UUID,
    payload: AnswerRelevancePromptUpdate,
    session: SessionDep,
    auth: MultitenantAuthDep,
) -> APIResponse[AnswerRelevancePromptResponse]:
    obj = answer_relevance_prompt_crud.update(
        session, id, auth.organization_id, auth.project_id, payload
    )
    return APIResponse.success_response(data=obj)


@router.delete(
    "/{id}",
    description=load_description("answer_relevance_prompts/delete_prompt.md"),
    response_model=APIResponse[dict],
)
def delete_answer_relevance_prompt(
    id: UUID,
    session: SessionDep,
    auth: MultitenantAuthDep,
) -> APIResponse[dict]:
    obj = answer_relevance_prompt_crud.get(
        session, id, auth.organization_id, auth.project_id
    )
    answer_relevance_prompt_crud.delete(session, obj)
    return APIResponse.success_response(
        data={"message": "Answer relevance prompt deleted successfully"}
    )
