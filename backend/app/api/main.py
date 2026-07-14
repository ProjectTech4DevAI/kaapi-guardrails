from fastapi import APIRouter

from app.api.routes import (
    ban_lists,
    guardrails,
    llm_prompt_configs,
    validator_configs,
    utils,
)

api_router = APIRouter()
api_router.include_router(ban_lists.router)
api_router.include_router(guardrails.router)
api_router.include_router(llm_prompt_configs.router)
api_router.include_router(validator_configs.router)
api_router.include_router(utils.router)

# if settings.ENVIRONMENT == "local":
#     api_router.include_router(private.router)
