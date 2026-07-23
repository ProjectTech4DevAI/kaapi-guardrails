from collections.abc import Generator
from dataclasses import dataclass
from typing import Annotated

import hashlib
import secrets

from fastapi import Depends, Header, HTTPException, Request, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session

from app.core.config import settings
from app.core.db import engine


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]


security = HTTPBearer(auto_error=False)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
    )


@dataclass
class TenantContext:
    organization_id: int
    project_id: int


def verify_caller(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(security),
    ],
    organization_id: Annotated[int, Header(alias="X-ORGANIZATION-ID")],
    project_id: Annotated[int, Header(alias="X-PROJECT-ID")],
) -> TenantContext:
    """
    Authenticates the single trusted caller (kaapi-backend) by static bearer token
    and source IP, and returns the tenant it resolved from the end user's API key.

    Tenant scope is never read from the query string or request body, so a route
    cannot be tenant-unscoped: the dependency that authenticates it also supplies
    the tenant.
    """
    if settings.ALLOWED_IPS:
        client_ip = request.client.host if request.client else None
        if client_ip not in settings.ALLOWED_IPS:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden",
            )

    if credentials is None:
        raise _unauthorized("Missing Authorization header")

    if not secrets.compare_digest(
        _hash_token(credentials.credentials),
        settings.AUTH_TOKEN,
    ):
        raise _unauthorized("Invalid authorization token")

    return TenantContext(organization_id=organization_id, project_id=project_id)


AuthDep = Annotated[TenantContext, Depends(verify_caller)]
