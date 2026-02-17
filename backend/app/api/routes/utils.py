from fastapi import APIRouter
from app.utils import load_description

router = APIRouter(prefix="/utils", tags=["utils"])


@router.get(
    "/health-check/",
    description=load_description("utils/health_check.md"),
)
def health_check() -> bool:
    return True
