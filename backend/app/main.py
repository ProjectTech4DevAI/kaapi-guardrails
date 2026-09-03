from asgi_correlation_id.middleware import CorrelationIdMiddleware
from fastapi import FastAPI
from fastapi.routing import APIRoute

from app.core.logging_config import setup_logging

setup_logging()

from app.api.main import api_router  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.exception_handlers import register_exception_handlers  # noqa: E402
from app.core.middleware import http_request_logger  # noqa: E402
from app.core.telemetry import setup_telemetry  # noqa: E402
from app.load_env import load_environment  # noqa: E402

# Load environment variables
load_environment()


def custom_generate_unique_id(route: APIRoute) -> str:
    tag = route.tags[0] if route.tags else "default"
    return f"{tag}-{route.name}"


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
)

app.middleware("http")(http_request_logger)
app.add_middleware(CorrelationIdMiddleware)

app.include_router(api_router, prefix=settings.API_V1_STR)

register_exception_handlers(app)

setup_telemetry(app)
