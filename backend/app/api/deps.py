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


# ============================================================
# Database Dependency
# ============================================================


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]


# ============================================================
# Static Bearer Token Authentication
# ============================================================

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
    ]
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


# ============================================================
# Multitenant API Key Authentication (For Ban list)
# ============================================================


@dataclass
class TenantContext:
    organization_id: int
    project_id: int


def _fetch_tenant_from_backend(token: str) -> TenantContext:
    if not settings.KAAPI_BACKEND_CREDENTIAL_URL:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="KAAPI_BACKEND_CREDENTIAL_URL is not configured",
        )

    try:
        response = httpx.get(
            settings.KAAPI_BACKEND_CREDENTIAL_URL,
            headers={"X-API-KEY": f"ApiKey {token}"},
            timeout=5,
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth service unavailable",
        )

    if response.status_code != 200:
        raise _unauthorized("Invalid API key")

    try:
        data = response.json()
    except ValueError:
        raise _unauthorized("Invalid API key")

    if not isinstance(data, dict) or not data.get("success"):
        raise _unauthorized("Invalid API key")

    records = data.get("data")
    if not isinstance(records, list) or not records:
        raise _unauthorized("Invalid API key")

    record = records[0]

    try:
        return TenantContext(
            organization_id=int(record["organization_id"]),
            project_id=int(record["project_id"]),
        )
    except (KeyError, TypeError, ValueError):
        raise _unauthorized("Invalid API key")


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
