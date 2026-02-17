from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.api.deps import MultitenantAuthDep, SessionDep
from app.core.exception_handlers import _safe_error_message
from app.crud.ban_list import ban_list_crud
from app.schemas.ban_list import BanListCreate, BanListUpdate, BanListResponse
from app.utils import APIResponse

router = APIRouter(prefix="/guardrails/ban_lists", tags=["Ban Lists"])


@router.post("/", response_model=APIResponse[BanListResponse])
def create_ban_list(
    payload: BanListCreate,
    session: SessionDep,
    auth: MultitenantAuthDep,
):
    try:
        response_model = ban_list_crud.create(
            session, payload, auth.organization_id, auth.project_id
        )
        return APIResponse.success_response(data=response_model)
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise exc
        return APIResponse.failure_response(error=_safe_error_message(exc))


@router.get("/", response_model=APIResponse[list[BanListResponse]])
def list_ban_lists(
    session: SessionDep,
    auth: MultitenantAuthDep,
    domain: Optional[str] = None,
):
    try:
        response_model = ban_list_crud.list(
            session, auth.organization_id, auth.project_id, domain
        )
        return APIResponse.success_response(data=response_model)
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise exc
        return APIResponse.failure_response(error=_safe_error_message(exc))


@router.get("/{id}", response_model=APIResponse[BanListResponse])
def get_ban_list(
    id: UUID,
    session: SessionDep,
    auth: MultitenantAuthDep,
):
    try:
        obj = ban_list_crud.get(session, id, auth.organization_id, auth.project_id)
        return APIResponse.success_response(data=obj)
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise exc
        return APIResponse.failure_response(error=_safe_error_message(exc))


@router.patch("/{id}", response_model=APIResponse[BanListResponse])
def update_ban_list(
    id: UUID,
    payload: BanListUpdate,
    session: SessionDep,
    auth: MultitenantAuthDep,
):
    try:
        response_model = ban_list_crud.update(
            session,
            id=id,
            organization_id=auth.organization_id,
            project_id=auth.project_id,
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
    session: SessionDep,
    auth: MultitenantAuthDep,
):
    try:
        obj = ban_list_crud.get(
            session,
            id,
            auth.organization_id,
            auth.project_id,
            require_owner=True,
        )
        ban_list_crud.delete(session, obj)
        return APIResponse.success_response(
            data={"message": "Ban list deleted successfully"}
        )
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise exc
        return APIResponse.failure_response(error=_safe_error_message(exc))
