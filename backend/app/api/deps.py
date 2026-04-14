from collections.abc import Generator
from dataclasses import dataclass
from typing import Annotated

import hashlib
import secrets
import httpx

from fastapi import Cookie, Depends, Header, HTTPException, Security, status
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


def _fetch_tenant_from_backend(headers: dict) -> TenantContext:
    if not settings.KAAPI_AUTH_URL:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="KAAPI_AUTH_URL is not configured",
        )

    try:
        response = httpx.get(
            f"{settings.KAAPI_AUTH_URL}/apikeys/verify",
            headers=headers,
            timeout=settings.KAAPI_AUTH_TIMEOUT,
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth service unavailable",
        )

    if response.status_code != 200:
        raise _unauthorized("Invalid credentials")

    data = response.json()
    if not isinstance(data, dict) or data.get("success") is not True:
        raise _unauthorized("Invalid credentials")

    record = data.get("data")
    if not isinstance(record, dict):
        raise _unauthorized("Invalid credentials")

    organization_id = record.get("organization_id")
    project_id = record.get("project_id")
    if not isinstance(organization_id, int) or not isinstance(project_id, int):
        raise _unauthorized("Invalid credentials")

    return TenantContext(
        organization_id=organization_id,
        project_id=project_id,
    )


def validate_multitenant_key(
    x_api_key: Annotated[str | None, Header(alias="X-API-KEY")] = None,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(security),
    ] = None,
    access_token: Annotated[str | None, Cookie(alias="access_token")] = None,
) -> TenantContext:
    if x_api_key and x_api_key.strip():
        return _fetch_tenant_from_backend({"X-API-KEY": x_api_key.strip()})

    if credentials is not None and credentials.credentials.strip():
        return _fetch_tenant_from_backend(
            {"Authorization": f"Bearer {credentials.credentials}"}
        )

    if access_token:
        return _fetch_tenant_from_backend({"Authorization": f"Bearer {access_token}"})

    raise _unauthorized(
        "Missing credentials: provide X-API-KEY header, Bearer token, or access_token cookie"
    )


MultitenantAuthDep = Annotated[
    TenantContext,
    Depends(validate_multitenant_key),
]
