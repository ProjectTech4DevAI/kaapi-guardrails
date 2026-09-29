import logging
import time

import sentry_sdk
from asgi_correlation_id import correlation_id
from fastapi import Request, Response

logger = logging.getLogger("http_request_logger")


async def http_request_logger(request: Request, call_next) -> Response:
    start_time = time.time()

    # Tag Sentry events with the request's correlation id and tenant.
    # set_tag is a safe no-op when Sentry is not initialized (tests, local).
    request_id = correlation_id.get()
    if request_id:
        sentry_sdk.set_tag("correlation_id", request_id)
    for header, tag in (
        ("X-ORGANIZATION-ID", "kaapi.organization_id"),
        ("X-PROJECT-ID", "kaapi.project_id"),
    ):
        value = request.headers.get(header)
        if value:
            sentry_sdk.set_tag(tag, value)

    try:
        response = await call_next(request)
    except Exception as e:
        logger.exception("Unhandled exception during request")
        raise

    process_time = (time.time() - start_time) * 1000  # ms
    client_ip = request.client.host if request.client else "unknown"

    logger.info(
        f"{request.method} {request.url.path} - {response.status_code} [{process_time:.2f}ms]"
    )
    return response
