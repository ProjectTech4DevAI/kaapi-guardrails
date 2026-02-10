from typing import Optional
from uuid import UUID

from fastapi import APIRouter

from app.api.deps import AuthDep, SessionDep
from app.core.enum import Stage, ValidatorType
from app.schemas.validator_config import (
    ValidatorCreate,
    ValidatorResponse,
    ValidatorUpdate,
)
from app.crud.validator_config import validator_config_crud
from app.utils import APIResponse


router = APIRouter(
    prefix="/guardrails/validators/configs",
    tags=["validator configs"],
)


@router.post("/", response_model=APIResponse[ValidatorResponse])
def create_validator(
    payload: ValidatorCreate,
    session: SessionDep,
    organization_id: int,
    project_id: int,
    _: AuthDep,
):
    response_model = validator_config_crud.create(
        session, organization_id, project_id, payload
    )
    return APIResponse.success_response(data=response_model)


@router.get("/", response_model=APIResponse[list[ValidatorResponse]])
def list_validators(
    organization_id: int,
    project_id: int,
    session: SessionDep,
    _: AuthDep,
    stage: Optional[Stage] = None,
    type: Optional[ValidatorType] = None,
):
    response_model = validator_config_crud.list(
        session, organization_id, project_id, stage, type
    )
    return APIResponse.success_response(data=response_model)


@router.get("/{id}", response_model=APIResponse[ValidatorResponse])
def get_validator(
    id: UUID,
    organization_id: int,
    project_id: int,
    session: SessionDep,
    _: AuthDep,
):
    obj = validator_config_crud.get(session, id, organization_id, project_id)
    return APIResponse.success_response(data=validator_config_crud.flatten(obj))


@router.patch("/{id}", response_model=APIResponse[ValidatorResponse])
def update_validator(
    id: UUID,
    organization_id: int,
    project_id: int,
    payload: ValidatorUpdate,
    session: SessionDep,
    _: AuthDep,
):
    obj = validator_config_crud.get(session, id, organization_id, project_id)
    response_model = validator_config_crud.update(
        session, obj, payload.model_dump(exclude_unset=True)
    )
    return APIResponse.success_response(data=response_model)


@router.delete("/{id}", response_model=APIResponse[dict])
def delete_validator(
    id: UUID,
    organization_id: int,
    project_id: int,
    session: SessionDep,
    _: AuthDep,
):
    obj = validator_config_crud.get(session, id, organization_id, project_id)
    validator_config_crud.delete(session, obj)
    return APIResponse.success_response(
        data={"message": "Validator deleted successfully"}
    )
