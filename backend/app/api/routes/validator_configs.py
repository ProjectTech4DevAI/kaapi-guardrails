from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import IntegrityError
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

    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=400,
            detail="Validator already exists for this type and stage",
        )

    session.refresh(obj)
    return flatten_validator(obj)

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
    obj = get_validator_or_404(id, org_id, project_id, session)
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
    obj = get_validator_or_404(id, org_id, project_id, session)
    updated_obj = update_validator_config(
        obj,
        payload.model_dump(exclude_unset=True),
        session
    )
    return flatten_validator(updated_obj)


@router.delete("/{id}")
async def delete_validator(
    id: UUID,
    org_id: int,
    project_id: int,
    session: SessionDep,
    _: AuthDep,
):
    obj = get_validator_or_404(id, org_id, project_id, session)
    session.delete(obj)
    session.commit()
    return {"success": True}

def flatten_validator(row: ValidatorConfig) -> dict:
    """
    Flatten validator config: combines base fields with config dict.
    Returns a dict with all fields including config extras.
    """
    base = row.model_dump(exclude={"config"})
    flattened = {**base, **(row.config or {})}
    print("FLATTENED:", flattened)
    return flattened


def get_validator_or_404(
    id: UUID,
    org_id: int,
    project_id: int,
    session: SessionDep,
) -> ValidatorConfig:
    """Fetch validator by id, org_id, and project_id, or raise 404."""
    obj = session.query(ValidatorConfig).filter(
        ValidatorConfig.id == id,
        ValidatorConfig.org_id == org_id,
        ValidatorConfig.project_id == project_id
    ).first()

    if not obj:
        raise HTTPException(status_code=404, detail="Validator not found")

    return obj


def update_validator_config(
    obj: ValidatorConfig,
    update_data: dict,
    session: SessionDep,
) -> ValidatorConfig:
    """Update validator config fields and return the updated object."""
    base, config = split_validator_payload(update_data)

    for k, v in base.items():
        setattr(obj, k, v)

    if config:
        obj.config = {**(obj.config or {}), **config}

    session.add(obj)
    session.commit()
    session.refresh(obj)

    return obj
