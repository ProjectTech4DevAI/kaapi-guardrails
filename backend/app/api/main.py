from fastapi import APIRouter

from app.api.routes import utils, guardrails

api_router = APIRouter()
api_router.include_router(utils.router)
api_router.include_router(guardrails.router)

# if settings.ENVIRONMENT == "local":
#     api_router.include_router(private.router)
