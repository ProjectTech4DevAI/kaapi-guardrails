from fastapi import APIRouter, HTTPException
from guardrails import Guard
from app.models.guardrail_config import GuardrailInputRequest, GuardrailOutputRequest
from app.api.deps import AuthDep

router = APIRouter(prefix="/guardrails", tags=["guardrails"])

@router.post("/input/")
async def run_input_guardrails(
    payload: GuardrailInputRequest,
    _: AuthDep,
):
    response_id = "ABC"

    try:
        guard = build_guard(payload.validators)
        result = guard.validate(payload.input)

        if result.validated_output is not None:
            return {
                "response_id": response_id,
                "safe_input": result.validated_output,
            }

        return {
            "response_id": response_id,
            "error": {
                "type": "validation_error",
                "action": "reask" if result.failures else "fail",
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "response_id": response_id,
                "error": {
                    "type": "config_error",
                    "reason": str(e),
                },
            },
        )


@router.post("/output")
async def run_output_guardrails(
    payload: GuardrailOutputRequest,
    _: AuthDep,
):
    response_id = "ABC"

    try:
        guard = build_guard(payload.validators)
        result = guard.validate(payload.output)

        if result.validated_output is not None:
            return {
                "response_id": response_id,
                "safe_input": result.validated_output,
            }

        return {
            "response_id": response_id,
            "error": {
                "type": "validation_error",
                "action": "reask" if result.failures else "fail",
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "response_id": response_id,
                "error": {
                    "type": "config_error",
                    "reason": str(e),
                },
            },
        )

def build_guard(validator_items):
    validators = [v_item.build() for v_item in validator_items]
    return Guard().use_many(*validators)