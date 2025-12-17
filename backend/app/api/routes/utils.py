from fastapi import APIRouter
from app.api.deps import AuthDep

router = APIRouter(prefix="/utils", tags=["utils"])

@router.get("/health-check/")
async def health_check(
    _: AuthDep
) -> bool:
    return True