from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.api.deps import AuthDep, SessionDep
from app.core.exception_handlers import _safe_error_message
from app.crud.ban_list import ban_list_crud
from app.schemas.ban_list import BanListCreate, BanListUpdate, BanListResponse
from app.utils import APIResponse

router = APIRouter(prefix="/guardrails/ban_lists", tags=["Ban Lists"])


@router.post("/", response_model=APIResponse[BanListResponse])
def create_ban_list(
    payload: BanListCreate,
    session: SessionDep,
    organization_id: int,
    project_id: int,
    _: AuthDep,
):
    try:
        response_model = ban_list_crud.create(
            session, payload, organization_id, project_id
        )
        return APIResponse.success_response(data=response_model)
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise exc
        return APIResponse.failure_response(error=_safe_error_message(exc))


@router.get("/", response_model=APIResponse[list[BanListResponse]])
def list_ban_lists(
    organization_id: int,
    project_id: int,
    session: SessionDep,
    _: AuthDep,
    domain: Optional[str] = None,
):
    try:
        response_model = ban_list_crud.list(
            session, organization_id, project_id, domain
        )
        return APIResponse.success_response(data=response_model)
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise exc
        return APIResponse.failure_response(error=_safe_error_message(exc))


@router.get("/{id}", response_model=APIResponse[BanListResponse])
def get_ban_list(
    id: UUID,
    organization_id: int,
    project_id: int,
    session: SessionDep,
    _: AuthDep,
):
    try:
        obj = ban_list_crud.get(session, id, organization_id, project_id)
        return APIResponse.success_response(data=obj)
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise exc
        return APIResponse.failure_response(error=_safe_error_message(exc))


@router.patch("/{id}", response_model=APIResponse[BanListResponse])
def update_ban_list(
    id: UUID,
    organization_id: int,
    project_id: int,
    payload: BanListUpdate,
    session: SessionDep,
    _: AuthDep,
):
    try:
        response_model = ban_list_crud.update(
            session,
            id=id,
            organization_id=organization_id,
            project_id=project_id,
            data=payload,
        )
        return APIResponse.success_response(data=response_model)
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise exc
        return APIResponse.failure_response(error=_safe_error_message(exc))


@router.delete("/{id}", response_model=APIResponse[dict])
def delete_ban_list(
    id: UUID,
    organization_id: int,
    project_id: int,
    session: SessionDep,
    _: AuthDep,
):
    try:
        obj = ban_list_crud.get(
            session, id, organization_id, project_id, require_owner=True
        )
        ban_list_crud.delete(session, obj)
        return APIResponse.success_response(
            data={"message": "Ban list deleted successfully"}
        )
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise exc
        return APIResponse.failure_response(error=_safe_error_message(exc))
