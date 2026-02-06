from typing import Optional
from uuid import UUID

from fastapi import APIRouter

from app.api.deps import AuthDep, SessionDep
from app.core.enum import Stage, ValidatorType
from app.schemas.validator_config import ValidatorCreate, ValidatorResponse, ValidatorUpdate
from app.crud.validator_config_crud import validator_config_crud


router = APIRouter(
    prefix="/guardrails/validators/configs",
    tags=["validator configs"],
)


@router.post(
        "/",
        response_model=ValidatorResponse
    )
async def create_validator(
    payload: ValidatorCreate,
    session: SessionDep,
    organization_id: int,
    project_id: int,
    _: AuthDep,
):
    return validator_config_crud.create(session, organization_id, project_id, payload)
@router.get(
        "/",
        response_model=list[ValidatorResponse]
    )
async def list_validators(
    organization_id: int,
    project_id: int,
    session: SessionDep,
    _: AuthDep,
    stage: Optional[Stage] = None,
    type: Optional[ValidatorType] = None,
):
    return validator_config_crud.list(session, organization_id, project_id, stage, type)


@router.get(
        "/{id}",
        response_model=ValidatorResponse
    )
async def get_validator(
    id: UUID,
    organization_id: int,
    project_id: int,
    session: SessionDep,
    _: AuthDep,
):
    obj = validator_config_crud.get_or_404(session, id, organization_id, project_id)
    return validator_config_crud.flatten(obj)


@router.patch(
        "/{id}",
        response_model=ValidatorResponse
    )
async def update_validator(
    id: UUID,
    organization_id: int,
    project_id: int,
    payload: ValidatorUpdate,
    session: SessionDep,
    _: AuthDep,
):
    obj = validator_config_crud.get_or_404(session, id, organization_id, project_id)
    return validator_config_crud.update(
        session,
        obj,
        payload.model_dump(exclude_unset=True),
    )


@router.delete("/{id}")
async def delete_validator(
    id: UUID,
    organization_id: int,
    project_id: int,
    session: SessionDep,
    _: AuthDep,
):
    obj = validator_config_crud.get_or_404(session, id, organization_id, project_id)
    validator_config_crud.delete(session, obj)
    return {"success": True}
