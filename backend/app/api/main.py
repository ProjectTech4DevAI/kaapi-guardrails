from fastapi import APIRouter

from app.api.routes import utils

api_router = APIRouter()
api_router.include_router(utils.router)


# if settings.ENVIRONMENT == "local":
#     api_router.include_router(private.router)
