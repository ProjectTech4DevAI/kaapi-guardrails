from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session

# from app.core import security
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

    token = credentials.credentials

    if token != settings.AUTH_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    return True

AuthDep = Annotated[bool, Depends(verify_bearer_token)]
