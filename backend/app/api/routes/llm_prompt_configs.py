from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import AuthDep, SessionDep
from app.core.enum import LLMValidatorName
from app.crud.llm_prompt_config import llm_prompt_config_crud
from app.schemas.llm_prompt_config import (
    LLMPromptConfigCreate,
    LLMPromptConfigResponse,
    LLMPromptConfigUpdate,
)
from app.utils import APIResponse, load_description

router = APIRouter(
    prefix="/guardrails/llm_prompt_configs",
    tags=["LLM Prompt Configs"],
)


@router.post(
    "/",
    description=load_description("llm_prompt_configs/create_config.md"),
    response_model=APIResponse[LLMPromptConfigResponse],
)
def create_llm_prompt_config(
    payload: LLMPromptConfigCreate,
    session: SessionDep,
    auth: AuthDep,
) -> APIResponse[LLMPromptConfigResponse]:
    obj = llm_prompt_config_crud.create(
        session,
        payload,
        auth.organization_id,
        auth.project_id,
    )
    return APIResponse.success_response(data=obj)


@router.get(
    "/",
    description=load_description("llm_prompt_configs/list_configs.md"),
    response_model=APIResponse[list[LLMPromptConfigResponse]],
)
def list_llm_prompt_configs(
    session: SessionDep,
    auth: AuthDep,
    validator_name: Annotated[LLMValidatorName | None, Query()] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int | None, Query(ge=1, le=100)] = None,
) -> APIResponse[list[LLMPromptConfigResponse]]:
    objs = llm_prompt_config_crud.list(
        session,
        auth.organization_id,
        auth.project_id,
        validator_name=validator_name,
        offset=offset,
        limit=limit,
    )
    return APIResponse.success_response(data=objs)


@router.get(
    "/{id}",
    description=load_description("llm_prompt_configs/get_config.md"),
    response_model=APIResponse[LLMPromptConfigResponse],
)
def get_llm_prompt_config(
    id: UUID,
    session: SessionDep,
    auth: AuthDep,
) -> APIResponse[LLMPromptConfigResponse]:
    obj = llm_prompt_config_crud.get(
        session,
        id,
        auth.organization_id,
        auth.project_id,
    )
    return APIResponse.success_response(data=obj)


@router.patch(
    "/{id}",
    description=load_description("llm_prompt_configs/update_config.md"),
    response_model=APIResponse[LLMPromptConfigResponse],
)
def update_llm_prompt_config(
    id: UUID,
    payload: LLMPromptConfigUpdate,
    session: SessionDep,
    auth: AuthDep,
) -> APIResponse[LLMPromptConfigResponse]:
    obj = llm_prompt_config_crud.update(
        session,
        id,
        auth.organization_id,
        auth.project_id,
        payload,
    )
    return APIResponse.success_response(data=obj)


@router.delete(
    "/{id}",
    description=load_description("llm_prompt_configs/delete_config.md"),
    response_model=APIResponse[dict],
)
def delete_llm_prompt_config(
    id: UUID,
    session: SessionDep,
    auth: AuthDep,
) -> APIResponse[dict]:
    obj = llm_prompt_config_crud.get(
        session,
        id,
        auth.organization_id,
        auth.project_id,
    )
    llm_prompt_config_crud.delete(session, obj)
    return APIResponse.success_response(data={"message": "Config deleted successfully"})
