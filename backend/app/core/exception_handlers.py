from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.status import (
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from app.utils import APIResponse

def _format_validation_errors(errors: list[dict]) -> str:
    missing_fields = []
    invalid_fields = []

    for err in errors:
        loc = [x for x in err["loc"] if x != "body"]

        if not loc:
            continue

        field = ".".join(str(x) for x in loc)

        if err["msg"] == "Field required":
            missing_fields.append(field)
        else:
            invalid_fields.append(f"{field} ({err['msg']})")

    messages = []

    if missing_fields:
        messages.append(
            f"Missing required field(s): {', '.join(missing_fields)}"
        )

    if invalid_fields:
        messages.append(
            f"Invalid field(s): {', '.join(invalid_fields)}"
        )

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
