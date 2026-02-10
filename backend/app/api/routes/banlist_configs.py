from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.api.deps import AuthDep, SessionDep
from app.crud.banlist import banlist_crud
from app.schemas.banlist import (
    BanListCreate,
    BanListUpdate,
    BanListResponse
)
from app.utils import APIResponse

router = APIRouter(
    prefix="/guardrails/ban-lists", 
    tags=["Ban Lists"]
)

@router.post(
        "/", 
        response_model=APIResponse[BanListResponse]
    )
def create_banlist(
    payload: BanListCreate,
    session: SessionDep,
    organization_id: int,
    project_id: int,
    _: AuthDep,
):
    try:
        response_model = banlist_crud.create(session, payload, organization_id, project_id)
        return APIResponse.success_response(data=response_model)
    except HTTPException as exc:
        return APIResponse.failure_response(error=str(exc.detail))
    except Exception as exc:
        return APIResponse.failure_response(error=str(exc))

@router.get(
        "/", 
        response_model=APIResponse[list[BanListResponse]]
    )
def list_banlists(
    organization_id: int,
    project_id: int,
    session: SessionDep,
    _: AuthDep,
    domain: Optional[str] = None,
):
    try:
        response_model = banlist_crud.list(session, organization_id, project_id, domain)
        return APIResponse.success_response(data=response_model)
    except HTTPException as exc:
        return APIResponse.failure_response(error=str(exc.detail))
    except Exception as exc:
        return APIResponse.failure_response(error=str(exc))


@router.get(
        "/{id}",
        response_model=APIResponse[BanListResponse]
    )
def get_banlist(
    id: UUID,
    organization_id: int,
    project_id: int,
    session: SessionDep,
    _: AuthDep,
):
    try:
        obj = banlist_crud.get(session, id, organization_id, project_id)
        return APIResponse.success_response(data=obj)
    except HTTPException as exc:
        return APIResponse.failure_response(error=str(exc.detail))
    except Exception as exc:
        return APIResponse.failure_response(error=str(exc))


@router.patch(
        "/{id}",
        response_model=APIResponse[BanListResponse]
    )
def update_banlist(
    id: UUID,
    organization_id: int,
    project_id: int,
    payload: BanListUpdate,
    session: SessionDep,
    _: AuthDep,
):
    try:
        response_model = banlist_crud.update(
            session,
            id=id,
            organization_id=organization_id,
            project_id=project_id,
            data=payload,
        )
        return APIResponse.success_response(data=response_model)
    except HTTPException as exc:
        return APIResponse.failure_response(error=str(exc.detail))
    except Exception as exc:
        return APIResponse.failure_response(error=str(exc))

@router.delete(
        "/{id}",
        response_model=APIResponse[dict]
    )
def delete_banlist(
    id: UUID,
    organization_id: int,
    project_id: int,
    session: SessionDep,
    _: AuthDep,
):
    try:
        obj = banlist_crud.get(session, id, organization_id, project_id)
        banlist_crud.delete(session, obj)
        return APIResponse.success_response(data={"message": "Banlist deleted successfully"})
    except HTTPException as exc:
        return APIResponse.failure_response(error=str(exc.detail))
    except Exception as exc:
        return APIResponse.failure_response(error=str(exc))
