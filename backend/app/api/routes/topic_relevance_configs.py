from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import MultitenantAuthDep, SessionDep
from app.crud.topic_relevance import topic_relevance_crud
from app.schemas.topic_relevance import (
    TopicRelevanceCreate,
    TopicRelevanceUpdate,
    TopicRelevanceResponse,
)
from app.utils import APIResponse, load_description

router = APIRouter(
    prefix="/guardrails/topic_relevance_configs",
    tags=["Topic Relevance Configs"],
)


@router.post(
    "/",
    description=load_description(
        "topic_relevance_configs/create_topic_relevance_config.md"
    ),
    response_model=APIResponse[TopicRelevanceResponse],
)
def create_topic_relevance_config(
    payload: TopicRelevanceCreate,
    session: SessionDep,
    auth: MultitenantAuthDep,
):
    topic_relevance_config = topic_relevance_crud.create(
        session,
        payload,
        auth.organization_id,
        auth.project_id,
    )
    return APIResponse.success_response(data=topic_relevance_config)


@router.get(
    "/",
    description=load_description(
        "topic_relevance_configs/list_topic_relevance_configs.md"
    ),
    response_model=APIResponse[list[TopicRelevanceResponse]],
)
def list_topic_relevance_configs(
    session: SessionDep,
    auth: MultitenantAuthDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int | None, Query(ge=1, le=100)] = None,
):
    topic_relevance_configs = topic_relevance_crud.list(
        session,
        auth.organization_id,
        auth.project_id,
        offset,
        limit,
    )
    return APIResponse.success_response(data=topic_relevance_configs)


@router.get(
    "/{id}",
    description=load_description(
        "topic_relevance_configs/get_topic_relevance_config.md"
    ),
    response_model=APIResponse[TopicRelevanceResponse],
)
def get_topic_relevance_config(
    id: UUID,
    session: SessionDep,
    auth: MultitenantAuthDep,
):
    topic_relevance_config = topic_relevance_crud.get(
        session,
        id,
        auth.organization_id,
        auth.project_id,
    )
    return APIResponse.success_response(data=topic_relevance_config)


@router.patch(
    "/{id}",
    description=load_description(
        "topic_relevance_configs/update_topic_relevance_config.md"
    ),
    response_model=APIResponse[TopicRelevanceResponse],
)
def update_topic_relevance_config(
    id: UUID,
    payload: TopicRelevanceUpdate,
    session: SessionDep,
    auth: MultitenantAuthDep,
):
    topic_relevance_config = topic_relevance_crud.update(
        session,
        id,
        auth.organization_id,
        auth.project_id,
        payload,
    )
    return APIResponse.success_response(data=topic_relevance_config)


@router.delete(
    "/{id}",
    description=load_description(
        "topic_relevance_configs/delete_topic_relevance_config.md"
    ),
    response_model=APIResponse[dict],
)
def delete_topic_relevance_config(
    id: UUID,
    session: SessionDep,
    auth: MultitenantAuthDep,
):
    obj = topic_relevance_crud.get(
        session,
        id,
        auth.organization_id,
        auth.project_id,
    )
    topic_relevance_crud.delete(session, obj)
    return APIResponse.success_response(data={"message": "Config deleted successfully"})
