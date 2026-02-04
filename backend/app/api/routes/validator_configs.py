from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select

from app.api.deps import AuthDep, SessionDep
from app.models.config.validator_config_table import ValidatorConfig
from app.schemas.validator_config import *
from app.utils import split_validator_payload

router = APIRouter(prefix="/guardrails/validators/configs", tags=["validator configs"])


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
    data = payload.model_dump()
    base, config = split_validator_payload(data)
    obj = ValidatorConfig(
        org_id=org_id,
        project_id=project_id,
        config=config,
        **base,
    )

    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj

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
    query = select(ValidatorConfig).where(
        ValidatorConfig.org_id == org_id,
        ValidatorConfig.project_id == project_id
    )

    if stage:
        query = query.where(ValidatorConfig.stage == stage)

    if type:
        query = query.where(ValidatorConfig.type == type)

    rows = session.exec(query).all()
    return [flatten_validator(r) for r in rows]


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
    obj = session.get(ValidatorConfig, id)

    if not obj or obj.org_id != org_id or obj.project_id != project_id:
        raise HTTPException(404)

    return flatten_validator(obj)


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
    obj = session.get(ValidatorConfig, id)

    if not obj or obj.org_id != org_id or obj.project_id != project_id:
        raise HTTPException(404)

    data = payload.model_dump(exclude_unset=True)
    base, config = split_validator_payload(data)

    print("base", base)
    print("config", config)
    for k, v in base.items():
        setattr(obj, k, v)

    if config:
        obj.config = {**(obj.config or {}), **config}

    session.add(obj)
    session.commit()
    session.refresh(obj)

    return flatten_validator(obj)


@router.delete("/{id}")
async def delete_validator(
    id: UUID,
    org_id: int,
    project_id: int,
    session: SessionDep,
    _: AuthDep,
):
    obj = session.get(ValidatorConfig, id)

    if not obj or obj.org_id != org_id or obj.project_id != project_id:
        raise HTTPException(404)

    session.delete(obj)
    session.commit()

    return {"success": True}

def flatten_validator(row: ValidatorConfig) -> dict:
    base = row.model_dump(exclude={"config"})

    print(base)
    return {**base, **(row.config or {})}
