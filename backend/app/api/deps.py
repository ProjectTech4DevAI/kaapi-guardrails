from collections.abc import Generator
from typing import Annotated
import hashlib
import secrets

from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session

from app.core.config import settings
from app.core.db import engine


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]
security = HTTPBearer(auto_error=False)


def verify_bearer_token(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(security),
    ]
):
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    provided_hash = _hash_token(credentials.credentials)
    print(provided_hash)
    expected_hash = settings.AUTH_TOKEN
    print(expected_hash)
    if not expected_hash:
        raise RuntimeError("AUTH_TOKEN is not configured")

    if not secrets.compare_digest(provided_hash, expected_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization token"
        )

    return True


AuthDep = Annotated[bool, Depends(verify_bearer_token)]
