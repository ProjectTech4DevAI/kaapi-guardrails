from fastapi import APIRouter

from app.api.routes import utils, guardrails, validator_configs

api_router = APIRouter()
api_router.include_router(utils.router)
api_router.include_router(guardrails.router)
api_router.include_router(validator_configs.router)

# if settings.ENVIRONMENT == "local":
#     api_router.include_router(private.router)
