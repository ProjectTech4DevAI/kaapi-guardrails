from collections.abc import Generator
from dataclasses import dataclass
from typing import Annotated

import hashlib
import secrets
import httpx

from fastapi import Depends, Header, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session

from app.core.config import settings
from app.core.db import engine


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]


# Static bearer token auth for internal routes.
security = HTTPBearer(auto_error=False)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
    )


def verify_bearer_token(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(security),
    ],
) -> bool:
    if credentials is None:
        raise _unauthorized("Missing Authorization header")

    if not secrets.compare_digest(
        _hash_token(credentials.credentials),
        settings.AUTH_TOKEN,
    ):
        raise _unauthorized("Invalid authorization token")

    return True


AuthDep = Annotated[bool, Depends(verify_bearer_token)]


# Multitenant auth context resolved from X-API-KEY.
@dataclass
class TenantContext:
    organization_id: int
    project_id: int


def _fetch_tenant_from_backend(token: str) -> TenantContext:
    if not settings.KAAPI_AUTH_URL:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="KAAPI_AUTH_URL is not configured",
        )

    try:
        response = httpx.get(
            f"{settings.KAAPI_AUTH_URL}/apikeys/verify",
            headers={"X-API-KEY": token},
            timeout=settings.KAAPI_AUTH_TIMEOUT,
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth service unavailable",
        )

    if response.status_code != 200:
        raise _unauthorized("Invalid API key")

    data = response.json()
    if not isinstance(data, dict) or data.get("success") is not True:
        raise _unauthorized("Invalid API key")

    record = data.get("data")
    if not isinstance(record, dict):
        raise _unauthorized("Invalid API key")

    organization_id = record.get("organization_id")
    project_id = record.get("project_id")
    if not isinstance(organization_id, int) or not isinstance(project_id, int):
        raise _unauthorized("Invalid API key")

    return TenantContext(
        organization_id=organization_id,
        project_id=project_id,
    )


def validate_multitenant_key(
    x_api_key: Annotated[str | None, Header(alias="X-API-KEY")] = None,
) -> TenantContext:
    if not x_api_key or not x_api_key.strip():
        raise _unauthorized("Missing X-API-KEY header")

    return _fetch_tenant_from_backend(x_api_key.strip())


MultitenantAuthDep = Annotated[
    TenantContext,
    Depends(validate_multitenant_key),
]
