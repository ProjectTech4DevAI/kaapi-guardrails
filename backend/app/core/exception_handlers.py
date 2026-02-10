from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.status import (
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from app.utils import APIResponse


def _format_validation_errors(errors: list[dict]) -> str:
    missing_fields: list[str] = []
    invalid_fields: list[str] = []
    body_missing = False

    for error in errors:
        raw_location = error["loc"]
        message = error["msg"]

        location_parts = [part for part in raw_location if part != "body"]

        if not location_parts:
            if message == "Field required":
                body_missing = True
            else:
                invalid_fields.append(f"body ({message})")
            continue

        field_path = ".".join(str(part) for part in location_parts)

        if message == "Field required":
            missing_fields.append(field_path)
        else:
            invalid_fields.append(f"{field_path} ({message})")

    messages: list[str] = []

    if body_missing:
        messages.append("Request body is required")

    if missing_fields:
        messages.append(f"Missing required field(s): {', '.join(missing_fields)}")

    if invalid_fields:
        messages.append(f"Invalid field(s): {', '.join(invalid_fields)}")

    return ". ".join(messages)


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        formatted_message = _format_validation_errors(exc.errors())
        return JSONResponse(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            content=APIResponse.failure_response(error=formatted_message).model_dump(),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=APIResponse.failure_response(exc.detail).model_dump(),
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content=APIResponse.failure_response(
                str(exc) or "An unexpected error occurred."
            ).model_dump(),
        )
