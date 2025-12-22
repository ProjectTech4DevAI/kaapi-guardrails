import uuid
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from app.models.guardrail_config import GuardrailInputRequest, GuardrailOutputRequest
from app.api.deps import AuthDep
from app.core.api_response import APIResponse
from app.core.guardrail_controller import build_guard, get_validator_config_models

router = APIRouter(prefix="/guardrails", tags=["guardrails"])

@router.post("/input/")
async def run_input_guardrails(
    payload: GuardrailInputRequest,
    _: AuthDep,
):
    response_id = str(uuid.uuid4())

    try:
        guard = build_guard(payload.validators)
        result = guard.validate(payload.input)

        if result.validated_output is not None:
            return APIResponse.success_response(
                data={
                    "response_id": response_id,
                    "safe_input": result.validated_output,
                }
            )

        # validation failure → 400
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=APIResponse.failure_response(
                error={
                    "response_id": response_id,
                    "type": "validation_error",
                    "action": "reask" if result.failures else "fail",
                    "failures": [
                        f.failure_message for f in (result.failures or [])
                    ],
                }
            ).model_dump(),
        )

    except Exception as e:
        # config/runtime error → 500
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=APIResponse.failure_response(
                error={
                    "response_id": response_id,
                    "type": "config_error",
                    "reason": str(e),
                }
            ).model_dump(),
        )


@router.post("/output")
async def run_output_guardrails(
    payload: GuardrailOutputRequest,
    _: AuthDep,
):
    response_id = str(uuid.uuid4())

    try:
        guard = build_guard(payload.validators)
        result = guard.validate(payload.output)

        if result.validated_output is not None:
            return APIResponse.success_response(
                data={
                    "response_id": response_id,
                    "safe_output": result.validated_output,
                }
            )

        # validation failure → 400
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=APIResponse.failure_response(
                error={
                    "response_id": response_id,
                    "type": "validation_error",
                    "action": "reask" if result.failures else "fail",
                    "failures": [
                        f.failure_message for f in (result.failures or [])
                    ],
                }
            ).model_dump(),
        )

    except Exception as e:
        # config/runtime error → 500
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=APIResponse.failure_response(
                error={
                    "response_id": response_id,
                    "type": "config_error",
                    "reason": str(e),
                }
            ).model_dump(),
        )

@router.get("/validator/")
async def list_validators(_: AuthDep):
    """
    Lists all validators and their parameters directly.
    """
    validator_config_models = get_validator_config_models()
    validators = []

    for model in validator_config_models:
        schema = model.model_json_schema()
        validator_type = schema["properties"]["type"]["const"]
        validators.append({
            "type": validator_type,
            "config": schema,
        })

    return {"validators": validators}