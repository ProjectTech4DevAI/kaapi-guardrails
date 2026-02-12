from fastapi import APIRouter

from app.api.routes import banlist_configs, guardrails, validator_configs, utils

api_router = APIRouter()
api_router.include_router(banlist_configs.router)
api_router.include_router(guardrails.router)
api_router.include_router(validator_configs.router)
api_router.include_router(utils.router)

# if settings.ENVIRONMENT == "local":
#     api_router.include_router(private.router)
