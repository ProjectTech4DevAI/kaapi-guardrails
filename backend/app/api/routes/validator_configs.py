from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter

from app.api.deps import AuthDep, SessionDep
from app.schemas.validator_config import *
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
    org_id: int,
    project_id: int,
    _: AuthDep,
):
    return validator_config_crud.create(session, org_id, project_id, payload)

@router.get(
        "/",
        response_model=List[ValidatorResponse]
    )
async def list_validators(
    org_id: int,
    project_id: int,
    session: SessionDep,
    _: AuthDep,
    stage: Optional[Stage] = None,
    type: Optional[ValidatorType] = None,
):
    return validator_config_crud.list(session, org_id, project_id, stage, type)


@router.get(
        "/{id}",
        response_model=ValidatorResponse
    )
async def get_validator(
    id: UUID,
    org_id: int,
    project_id: int,
    session: SessionDep,
    _: AuthDep,
):
    obj = validator_config_crud.get_or_404(session, id, org_id, project_id)
    return validator_config_crud._flatten(obj)


@router.patch(
        "/{id}",
        response_model=ValidatorResponse
    )
async def update_validator(
    id: UUID,
    org_id: int,
    project_id: int,
    payload: ValidatorUpdate,
    session: SessionDep,
    _: AuthDep,
):
    obj = validator_config_crud.get_or_404(session, id, org_id, project_id)
    return validator_config_crud.update(
        session,
        obj,
        payload.model_dump(exclude_unset=True),
    )


@router.delete("/{id}")
async def delete_validator(
    id: UUID,
    org_id: int,
    project_id: int,
    session: SessionDep,
    _: AuthDep,
):
    obj = validator_config_crud.get_or_404(session, id, org_id, project_id)
    validator_config_crud.delete(session, obj)
    return {"success": True}
