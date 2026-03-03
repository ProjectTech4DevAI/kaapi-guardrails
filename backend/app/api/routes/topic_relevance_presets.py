from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import MultitenantAuthDep, SessionDep
from app.crud.topic_relevance_preset import topic_relevance_preset_crud
from app.schemas.topic_relevance_preset import (
    TopicRelevancePresetCreate,
    TopicRelevancePresetUpdate,
    TopicRelevancePresetResponse,
)
from app.utils import APIResponse, load_description

router = APIRouter(
    prefix="/guardrails/topic_relevance_presets",
    tags=["Topic Relevance Presets"],
)


@router.post(
    "/",
    description="Create topic relevance preset",
    response_model=APIResponse[TopicRelevancePresetResponse],
)
def create_preset(
    payload: TopicRelevancePresetCreate,
    session: SessionDep,
    auth: MultitenantAuthDep,
):
    preset = topic_relevance_preset_crud.create(
        session,
        payload,
        auth.organization_id,
        auth.project_id,
    )
    return APIResponse.success_response(data=preset)


@router.get(
    "/",
    response_model=APIResponse[list[TopicRelevancePresetResponse]],
)
def list_presets(
    session: SessionDep,
    auth: MultitenantAuthDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int | None, Query(ge=1, le=100)] = None,
):
    presets = topic_relevance_preset_crud.list(
        session,
        auth.organization_id,
        auth.project_id,
        offset,
        limit,
    )
    return APIResponse.success_response(data=presets)


@router.get(
    "/{id}",
    response_model=APIResponse[TopicRelevancePresetResponse],
)
def get_preset(
    id: UUID,
    session: SessionDep,
    auth: MultitenantAuthDep,
):
    preset = topic_relevance_preset_crud.get(
        session,
        id,
        auth.organization_id,
        auth.project_id,
    )
    return APIResponse.success_response(data=preset)


@router.patch(
    "/{id}",
    response_model=APIResponse[TopicRelevancePresetResponse],
)
def update_preset(
    id: UUID,
    payload: TopicRelevancePresetUpdate,
    session: SessionDep,
    auth: MultitenantAuthDep,
):
    preset = topic_relevance_preset_crud.update(
        session,
        id,
        auth.organization_id,
        auth.project_id,
        payload,
    )
    return APIResponse.success_response(data=preset)


@router.delete(
    "/{id}",
    response_model=APIResponse[dict],
)
def delete_preset(
    id: UUID,
    session: SessionDep,
    auth: MultitenantAuthDep,
):
    obj = topic_relevance_preset_crud.get(
        session,
        id,
        auth.organization_id,
        auth.project_id,
    )
    topic_relevance_preset_crud.delete(session, obj)
    return APIResponse.success_response(data={"message": "Preset deleted successfully"})
