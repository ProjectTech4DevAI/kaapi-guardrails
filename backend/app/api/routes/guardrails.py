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
    return await _validate_with_guard(
        payload.input,
        payload.validators,
        "safe_input"
    )

@router.post("/output")
async def run_output_guardrails(
    payload: GuardrailOutputRequest,
    _: AuthDep,
):
    return await _validate_with_guard(
        payload.input,
        payload.validators,
        "safe_output"
    )

@router.get("/validator/")
async def list_validators(_: AuthDep):
    """
    Lists all validators and their parameters directly.
    """
    validator_config_models = get_validator_config_models()
    validators = []

    for model in validator_config_models:
        try:
            schema = model.model_json_schema()
            validator_type = schema["properties"]["type"]["const"]
            validators.append({
                "type": validator_type,
                "config": schema,
            })
        except (KeyError, TypeError) as e:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=APIResponse.failure_response(
                    error={
                        "type": "internal_error",
                        "reason": f"Failed to retrieve schema for validator {model.__name__}: {str(e)}",
                    }
                ).model_dump(),
            )

    return {"validators": validators}

async def _validate_with_guard(
    data: str,
    validators: list,
    response_field: str  # "safe_input" or "safe_output"
) -> JSONResponse | APIResponse:
    response_id = str(uuid.uuid4())
    
    try:
        guard = build_guard(validators)
        result = guard.validate(data)
        
        if result.validated_output is not None:
            return APIResponse.success_response(
                data={
                    "response_id": response_id,
                    response_field: result.validated_output,
                }
            )
        
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