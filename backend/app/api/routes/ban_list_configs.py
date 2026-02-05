from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.api.deps import AuthDep, SessionDep
from app.crud.ban_list_crud import ban_list_crud
from app.schemas.ban_list_config import (
    BanListCreate,
    BanListUpdate,
    BanListResponse
)

router = APIRouter(
    prefix="/guardrails/ban-lists", 
    tags=["Ban Lists"]
)


def check_owner(obj, org_id, project_id):
    if obj.org_id != org_id or obj.project_id != project_id:
        raise HTTPException(status_code=403, detail="Not owner")


@router.post(
        "/", 
        response_model=BanListResponse
    )
def create_ban_list(
    payload: BanListCreate,
    session: SessionDep,
    org_id: int,
    project_id: int,
    _: AuthDep,
):
    return ban_list_crud.create(
        session,
        data=payload,
        org_id=org_id,
        project_id=project_id,
    )


@router.get(
        "/", 
        response_model=list[BanListResponse]
    )
def list_ban_lists(
    org_id: int,
    project_id: int,
    session: SessionDep,
    _: AuthDep,
    domain: Optional[str] = None,
):
    return ban_list_crud.list(
        session,
        org_id=org_id,
        project_id=project_id,
        domain=domain,
    )


@router.get(
        "/{id}",
        response_model=BanListResponse
    )
def get_ban_list(
    id: UUID,
    org_id: int,
    project_id: int,
    session: SessionDep,
    _: AuthDep,
):
    obj = ban_list_crud.get(session, id)
    if not obj:
        raise HTTPException(404)

    if not obj.is_public:
        check_owner(obj, org_id, project_id)
    return obj


@router.patch(
        "/{id}",
        response_model=BanListResponse
    )
def update_ban_list(
    id: UUID,
    org_id: int,
    project_id: int,
    payload: BanListUpdate,
    session: SessionDep,
    _: AuthDep,
):
    obj = ban_list_crud.get(session, id)
    if not obj:
        raise HTTPException(404)

    check_owner(obj, org_id, project_id)
    return ban_list_crud.update(session, obj=obj, data=payload)


@router.delete("/{id}")
def delete_ban_list(
    id: UUID,
    org_id: int,
    project_id: int,
    session: SessionDep,
    _: AuthDep,
):
    obj = ban_list_crud.get(session, id)
    if not obj:
        raise HTTPException(404)

    check_owner(obj, org_id, project_id)
    ban_list_crud.delete(session, obj)
    return {"success": True}
