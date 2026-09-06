import hashlib
import secrets
from collections.abc import Generator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
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


def check_source_ip(request: Request) -> None:
    """403 for callers whose source IP is not in ALLOWED_IPS."""
    if settings.ALLOWED_IPS:
        allowed = settings.ALLOWED_IPS
        if isinstance(allowed, str):
            allowed = [allowed]
        client_ip = request.client.host if request.client else None
        if client_ip not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Source IP '{client_ip}' is not permitted to access this service.",
            )


def check_bearer_token(
    _ip_ok: Annotated[None, Depends(check_source_ip)],
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(security),
    ],
) -> None:
    """401 for a missing or invalid bearer token."""
    if credentials is None:
        raise _unauthorized("Missing Authorization header")

    if not secrets.compare_digest(
        _hash_token(credentials.credentials),
        settings.AUTH_TOKEN,
    ):
        raise _unauthorized("Invalid authorization token")


def verify_caller(
    _token_ok: Annotated[None, Depends(check_bearer_token)],
    organization_id: Annotated[int, Header(alias="X-ORGANIZATION-ID")],
    project_id: Annotated[int, Header(alias="X-PROJECT-ID")],
) -> TenantContext:
    """Authenticates the trusted caller and returns its tenant scope."""
    return TenantContext(organization_id=organization_id, project_id=project_id)


AuthDep = Annotated[TenantContext, Depends(verify_caller)]
