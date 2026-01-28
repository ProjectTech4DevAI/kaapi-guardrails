import uuid
from uuid import UUID

from fastapi import APIRouter
from guardrails.guard import Guard
from guardrails.validators import FailResult

from app.api.deps import AuthDep, SessionDep
from app.core.guardrail_controller import build_guard, get_validator_config_models
from app.crud.request_log import RequestLogCrud
from app.crud.validator_log import ValidatorLogCrud
from app.models.guardrail_config import GuardrailInputRequest, GuardrailOutputRequest
from app.models.logging.request import  RequestLogUpdate, RequestStatus
from app.models.logging.validator import ValidatorLog, ValidatorOutcome
from app.utils import APIResponse

router = APIRouter(prefix="/guardrails", tags=["guardrails"])

@router.post("/input/")
async def run_input_guardrails(
    payload: GuardrailInputRequest,
    session: SessionDep,
    _: AuthDep,
):
    request_log_crud = RequestLogCrud(session=session)
    validator_log_crud = ValidatorLogCrud(session=session)
    request_id = None

    try:
        request_id = UUID(payload.request_id)
    except ValueError:
        return APIResponse.failure_response(error="Invalid request_id")

    request_log = request_log_crud.create(request_id, input_text=payload.input)    
    return await _validate_with_guard(
        payload.input,
        payload.validators,
        "safe_input",
        request_log_crud,
        request_log.id,
        validator_log_crud,
    )

@router.post("/output/")
async def run_output_guardrails(
    payload: GuardrailOutputRequest,
    session: SessionDep,
    _: AuthDep,
):
    request_log_crud = RequestLogCrud(session=session)
    validator_log_crud = ValidatorLogCrud(session=session)
    request_id = None

    try:
        request_id = UUID(payload.request_id)
    except ValueError:
        return APIResponse.failure_response(error="Invalid request_id")

    request_log = request_log_crud.create(request_id, input_text=payload.output)
    return await _validate_with_guard(
        payload.output,
        payload.validators,
        "safe_output",
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
    response_field: str,  # "safe_input" or "safe_output"
    request_log_crud: RequestLogCrud,
    request_log_id: UUID,
    validator_log_crud: ValidatorLogCrud,
) -> APIResponse:
    response_id = uuid.uuid4() 
    guard = None

    try:
        guard = build_guard(validators)
        result = guard.validate(data)

        if result.validated_output is not None:
            request_log_crud.update(
                request_log_id=request_log_id, 
                request_status=RequestStatus.SUCCESS,
                request_log_update= RequestLogUpdate(
                    response_text=result.validated_output, 
                    response_id=response_id
                    )
                )
            
            add_validator_logs(guard, request_log_id, validator_log_crud)

            return APIResponse.success_response(
                data={
                    "response_id": response_id,
                    response_field: result.validated_output,
                }
            )

        request_log_crud.update(
            request_log_id=request_log_id,
            request_status=RequestStatus.ERROR,
            request_log_update=RequestLogUpdate(
                response_text=str(result),
                response_id=response_id,
            ),
        )
        add_validator_logs(guard, request_log_id, validator_log_crud)
        return APIResponse.failure_response(
            data={
                "response_id": response_id,
                response_field: None,
            },
            error="Validation failed",
        )

    except Exception as e:
        request_log_crud.update(
            request_log_id=request_log_id, 
            request_status=RequestStatus.ERROR,
            request_log_update= RequestLogUpdate(
                response_text=str(e), 
                response_id=response_id
                )
            )

        add_validator_logs(guard, request_log_id, validator_log_crud)

        return APIResponse.failure_response(
            data={
                "response_id": response_id,
                response_field: None,
                },
            error=str(e),
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
