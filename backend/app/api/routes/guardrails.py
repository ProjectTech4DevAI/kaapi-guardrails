import uuid
from uuid import UUID

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.api.deps import AuthDep, SessionDep
from app.core.guardrail_controller import build_guard, get_validator_config_models
from app.crud.request_log import RequestLogCrud
from app.models.guardrail_config import GuardrailInputRequest, GuardrailOutputRequest
from app.models.request import  RequestLogUpdate, RequestStatus
from app.utils import APIResponse

router = APIRouter(prefix="/guardrails", tags=["guardrails"])

@router.post("/input/")
async def run_input_guardrails(
    payload: GuardrailInputRequest,
    session: SessionDep,
    _: AuthDep,
):
    request_log_crud = RequestLogCrud(session=session)
    request_log = request_log_crud.create(request_id=UUID(payload.request_id), input_text=payload.input)
    return await _validate_with_guard(
        payload.input,
        payload.validators,
        "safe_input",
        request_log_crud,
        request_log.id
    )

@router.post("/output/")
async def run_output_guardrails(
    payload: GuardrailOutputRequest,
    session: SessionDep,
    _: AuthDep,
):
    request_log_crud = RequestLogCrud(session=session)
    request_log = request_log_crud.create(request_id=UUID(payload.request_id), input_text=payload.output)
    return await _validate_with_guard(
        payload.output,
        payload.validators,
        "safe_output",
        request_log_crud,
        request_log.id
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
    request_log_id: UUID
) -> APIResponse:
    response_id = uuid.uuid4() 

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
            
            return APIResponse.success_response(
                data={
                    "response_id": response_id,
                    response_field: result.validated_output,
                }
            )
        
        error = ", ".join(f.failure_message for f in (result.failures or []))

        request_log_crud.update(
            request_log_id=request_log_id, 
            request_status=RequestStatus.ERROR,
            request_log_update= RequestLogUpdate(
                response_text=error,
                response_id=response_id
                )
            )
        return APIResponse.failure_response(
            data={
                "response_id": response_id,
                response_field: None,
                },
            error=error,
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
        return APIResponse.failure_response(
            data={
                "response_id": response_id,
                response_field: None,
                },
            error=str(e),
        )