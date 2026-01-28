import uuid
from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter
from guardrails.guard import Guard
from guardrails.validators import FailResult

from app.api.deps import AuthDep, SessionDep
from app.core.constants import REPHRASE_ON_FAIL_PREFIX, SAFE_INPUT_FIELD, SAFE_OUTPUT_FIELD
from app.core.guardrail_controller import build_guard, get_validator_config_models
from app.crud.request_log import RequestLogCrud
from app.crud.validator_log import ValidatorLogCrud
from app.models.guardrail_config import (
    GuardrailInputRequest,
    GuardrailOutputRequest,
    GuardrailInputResponse,
    GuardrailOutputResponse,
)
from app.models.logging.request import  RequestLogUpdate, RequestStatus
from app.models.logging.validator import ValidatorLog, ValidatorOutcome
from app.utils import APIResponse

router = APIRouter(prefix="/guardrails", tags=["guardrails"])

@router.post(
        "/input/",
        response_model=APIResponse[GuardrailInputResponse],
        response_model_exclude_none=True)
async def run_input_guardrails(
    payload: GuardrailInputRequest,
    session: SessionDep,
    _: AuthDep,
):
    request_log_crud = RequestLogCrud(session=session)
    validator_log_crud = ValidatorLogCrud(session=session)

    try:
        request_id = UUID(payload.request_id)
    except ValueError:
        return APIResponse.failure_response(error="Invalid request_id")

    request_log = request_log_crud.create(request_id, input_text=payload.input)    
    return await _validate_with_guard(
        payload.input,
        payload.validators,
        SAFE_INPUT_FIELD,
        request_log_crud,
        request_log.id,
        validator_log_crud,
    )

@router.post(
        "/output/",
        response_model=APIResponse[GuardrailOutputResponse],
        response_model_exclude_none=True)
async def run_output_guardrails(
    payload: GuardrailOutputRequest,
    session: SessionDep,
    _: AuthDep,
):
    request_log_crud = RequestLogCrud(session=session)
    validator_log_crud = ValidatorLogCrud(session=session)

    try:
        request_id = UUID(payload.request_id)
    except ValueError:
        return APIResponse.failure_response(error="Invalid request_id")

    request_log = request_log_crud.create(request_id, input_text=payload.output)
    return await _validate_with_guard(
        payload.output,
        payload.validators,
        SAFE_OUTPUT_FIELD,
        request_log_crud,
        request_log.id,
        validator_log_crud
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
            return APIResponse.failure_response(
                error=f"Failed to retrieve schema for validator {model.__name__}: {str(e)}",
            )

    return {"validators": validators}

async def _validate_with_guard(
    data: str,
    validators: list,
    response_type: str,  # "safe_input" or "safe_output"
    request_log_crud: RequestLogCrud,
    request_log_id: UUID,
    validator_log_crud: ValidatorLogCrud,
) -> APIResponse:
    """
    Runs Guardrails validation on input/output data, persists request & validator logs,
    and returns a structured APIResponse.

    This function treats validation failures as first-class outcomes (not exceptions),
    while still safely handling unexpected runtime errors.
    """
    response_id = uuid.uuid4() 
    guard: Guard | None = None

    def _finalize(
        *,
        status: RequestStatus,
        response_text: str | None,
        validated_output: str | None = None,
    ) -> APIResponse:
        """
        Single exit-point helper to ensure:
        - request logs are always updated
        - validator logs are written when available
        - API responses are consistent
        """
        request_log_crud.update(
            request_log_id=request_log_id,
            request_status=status,
            request_log_update=RequestLogUpdate(
                response_text=response_text,
                response_id=response_id,
            ),
        )

        if guard is not None:
            add_validator_logs(guard, request_log_id, validator_log_crud)

        rephrase_needed = (
            validated_output is not None
            and validated_output.startswith(REPHRASE_ON_FAIL_PREFIX)
        )

        if response_type == SAFE_INPUT_FIELD:
            response_model = GuardrailInputResponse(
                response_id=response_id,
                rephrase_needed=rephrase_needed,
                safe_input=validated_output,
            )
        else:
            response_model = GuardrailOutputResponse(
                response_id=response_id,
                rephrase_needed=rephrase_needed,
                safe_output=validated_output,
            )

        if status == RequestStatus.SUCCESS:
            return APIResponse.success_response(data=response_model)

        return APIResponse.failure_response(
            data=response_model,
            error=response_text or "Validation failed",
        )

    try:
        guard = build_guard(validators)
        result = guard.validate(data)

        # Case 1: validation passed OR failed-with-fix (on_fail=FIX)
        if result.validated_output is not None:
            return _finalize(
                status=RequestStatus.SUCCESS,
                response_text=result.validated_output,
                validated_output=result.validated_output,
            )

        # Case 2: validation failed without a fix
        return _finalize(
            status=RequestStatus.ERROR,
            response_text=str(result.error),
            validated_output=None,
        )

    except Exception as exc:
        # Case 3: unexpected system / runtime failure
        return _finalize(
            status=RequestStatus.ERROR,
            response_text=str(exc),
            validated_output=None,
        )

def add_validator_logs(guard: Guard, request_log_id: UUID, validator_log_crud: ValidatorLogCrud):
    if not guard or not guard.history or not guard.history.last:
        return

    call = guard.history.last
    if not call.iterations:
        return

    iteration = call.iterations[-1]
    if not iteration.outputs or not iteration.outputs.validator_logs:
        return

    for log in iteration.outputs.validator_logs:
        result = log.validation_result

        error_message = None
        if isinstance(result, FailResult):
            error_message = result.error_message

        validator_log = ValidatorLog(
            request_id=request_log_id,
            name=log.validator_name,
            input=str(log.value_before_validation),
            output=log.value_after_validation,
            error=error_message,
            outcome=ValidatorOutcome(result.outcome.upper()),
        )

        validator_log_crud.create(log=validator_log)
