from uuid import UUID
import uuid

from fastapi import APIRouter
from guardrails.guard import Guard
from guardrails.validators import FailResult, PassResult
from sqlmodel import Session

from app.api.deps import AuthDep, SessionDep
from app.core.constants import BAN_LIST, REPHRASE_ON_FAIL_PREFIX
from app.core.guardrail_controller import build_guard, get_validator_config_models
from app.core.exception_handlers import _safe_error_message
from app.core.validators.config.ban_list_safety_validator_config import (
    BanListSafetyValidatorConfig,
)
from app.crud.ban_list import ban_list_crud
from app.crud.topic_relevance import topic_relevance_crud
from app.crud.request_log import RequestLogCrud
from app.crud.validator_log import ValidatorLogCrud
from app.core.validators.config.topic_relevance_safety_validator_config import (
    TopicRelevanceSafetyValidatorConfig,
)
from app.schemas.guardrail_config import GuardrailRequest, GuardrailResponse
from app.models.logging.request_log import RequestLogUpdate, RequestStatus
from app.models.logging.validator_log import ValidatorLog, ValidatorOutcome
from app.utils import APIResponse, load_description

router = APIRouter(prefix="/guardrails", tags=["guardrails"])


@router.post(
    "/",
    description=load_description("guardrails/run_guardrails.md"),
    response_model=APIResponse[GuardrailResponse],
    response_model_exclude_none=True,
)
def run_guardrails(
    payload: GuardrailRequest,
    session: SessionDep,
    _: AuthDep,
    suppress_pass_logs: bool = True,
):
    """
    Resolves any config-backed validator references (ban list words, topic relevance scope),
    then runs validation and returns a structured guardrail response.
    """
    request_log_crud = RequestLogCrud(session=session)
    validator_log_crud = ValidatorLogCrud(session=session)

    try:
        request_log = request_log_crud.create(payload)
    except ValueError:
        return APIResponse.failure_response(error="Invalid request_id")

    _resolve_validator_configs(payload, session)
    return _validate_with_guard(
        payload,
        request_log_crud,
        request_log.id,
        validator_log_crud,
        suppress_pass_logs,
    )


@router.get("/", description=load_description("guardrails/list_validators.md"))
def list_validators(_: AuthDep):
    """
    Lists all validators and their parameters directly.
    """
    validator_config_models = get_validator_config_models()
    validators = []

    for model in validator_config_models:
        try:
            schema = model.model_json_schema()
            validator_type = schema["properties"]["type"]["const"]
            validators.append(
                {
                    "type": validator_type,
                    "config": schema,
                }
            )

        except (KeyError, TypeError) as e:
            return APIResponse.failure_response(
                error=(
                    "Failed to retrieve schema for validator "
                    f"{model.__name__}: {_safe_error_message(e)}"
                ),
            )

    return {"validators": validators}


def _resolve_validator_configs(payload: GuardrailRequest, session: Session) -> None:
    """
    Resolves config-backed references for all validators in-place before guard execution:
    - BanList: fetches banned_words from the stored BanList when not provided inline.
    - TopicRelevance: fetches configuration and prompt_schema_version from stored config.
    """
    for validator in payload.validators:
        if isinstance(validator, BanListSafetyValidatorConfig):
            if validator.type == BAN_LIST and validator.banned_words is None:
                ban_list = ban_list_crud.get(
                    session,
                    id=validator.ban_list_id,
                    organization_id=payload.organization_id,
                    project_id=payload.project_id,
                )
                validator.banned_words = ban_list.banned_words

        elif isinstance(validator, TopicRelevanceSafetyValidatorConfig):
            if validator.topic_relevance_config_id is not None:
                config = topic_relevance_crud.get(
                    session=session,
                    id=validator.topic_relevance_config_id,
                    organization_id=payload.organization_id,
                    project_id=payload.project_id,
                )
                validator.configuration = config.configuration
                validator.prompt_schema_version = config.prompt_schema_version


def _validate_with_guard(
    payload: GuardrailRequest,
    request_log_crud: RequestLogCrud,
    request_log_id: UUID,
    validator_log_crud: ValidatorLogCrud,
    suppress_pass_logs: bool = False,
) -> APIResponse:
    """
    Runs Guardrails validation on input/output data, persists request & validator logs,
    and returns a structured APIResponse.

    This function treats validation failures as first-class outcomes (not exceptions),
    while still safely handling unexpected runtime errors.
    """
    response_id = uuid.uuid4()
    data = payload.input
    validators = payload.validators
    guard: Guard | None = None

    def _finalize(
        *,
        status: RequestStatus,
        validated_output: str | None = None,
        error_message: str | None = None,
    ) -> APIResponse:
        """
        Single exit-point helper to ensure:
        - request logs are always updated
        - validator logs are written when available
        - API responses are consistent
        """
        response_text = (
            validated_output if validated_output is not None else error_message
        )
        if response_text is None:
            response_text = "Validation failed"

        request_log_crud.update(
            request_log_id=request_log_id,
            request_status=status,
            request_log_update=RequestLogUpdate(
                response_text=response_text,
                response_id=response_id,
            ),
        )

        if guard is not None:
            add_validator_logs(
                guard, request_log_id, validator_log_crud, payload, suppress_pass_logs
            )

        rephrase_needed = validated_output is not None and validated_output.startswith(
            REPHRASE_ON_FAIL_PREFIX
        )

        response_model = GuardrailResponse(
            response_id=response_id,
            rephrase_needed=rephrase_needed,
            safe_text=validated_output,
        )

        if status == RequestStatus.SUCCESS:
            meta = next(
                (v._validator_metadata for v in validators if v._validator_metadata),
                None,
            )
            return APIResponse.success_response(data=response_model, metadata=meta)

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
                validated_output=result.validated_output,
            )

        # Case 2: validation failed without a fix
        error_message = "Validation failed"

        history = getattr(guard, "history", None)
        if history and getattr(history, "last", None):
            iterations = getattr(history.last, "iterations", None)
            if iterations:
                iteration = iterations[-1]
                logs = getattr(
                    getattr(iteration, "outputs", None), "validator_logs", []
                )
                for log in logs:
                    log_result = log.validation_result
                    if isinstance(log_result, FailResult) and log_result.error_message:
                        if log.validator_name == "guardrails/llm_critic":
                            error_message = _normalize_llm_critic_error(
                                log_result.error_message
                            )
                        else:
                            error_message = _redact_input(
                                log_result.error_message, data
                            )
                        break

        return _finalize(
            status=RequestStatus.ERROR,
            error_message=error_message,
        )

    except Exception as exc:
        # Case 3: unexpected system / runtime failure
        safe_msg = _redact_input(_safe_error_message(exc), data)
        return _finalize(
            status=RequestStatus.ERROR,
            error_message=safe_msg,
        )


def _redact_input(error_message: str, input_text: str) -> str:
    error_message = error_message.split(":\n\n")[0]
    return error_message.replace(input_text, "")


def add_validator_logs(
    guard: Guard,
    request_log_id: UUID,
    validator_log_crud: ValidatorLogCrud,
    payload: GuardrailRequest,
    suppress_pass_logs: bool = False,
) -> None:
    """
    Writes a ValidatorLog entry for each validator outcome in the guard's last iteration.
    Pass results are skipped when suppress_pass_logs is True.
    """
    history = getattr(guard, "history", None)
    if not history:
        return

    last_call = getattr(history, "last", None)
    if not last_call or not getattr(last_call, "iterations", None):
        return

    iteration = last_call.iterations[-1]
    outputs = getattr(iteration, "outputs", None)
    if not outputs or not getattr(outputs, "validator_logs", None):
        return

    for log in iteration.outputs.validator_logs:
        result = log.validation_result

        if result is None:
            continue

        if suppress_pass_logs and isinstance(result, PassResult):
            continue

        error_message = None
        if isinstance(result, FailResult):
            error_message = result.error_message

        validator_log = ValidatorLog(
            request_id=request_log_id,
            organization_id=payload.organization_id,
            project_id=payload.project_id,
            name=log.validator_name,
            input=str(log.value_before_validation),
            output=log.value_after_validation,
            error=error_message,
            outcome=ValidatorOutcome(result.outcome.upper()),
        )

        validator_log_crud.create(log=validator_log)


def _normalize_llm_critic_error(message: str) -> str:
    if "failed the following metrics" in message:
        return "The response did not meet the required quality criteria."
    if "missing or has invalid evaluations" in message:
        return (
            "The LLM critic could not evaluate one or more metrics. "
            "The critic model returned an incomplete or malformed response. "
            "Please retry."
        )
    return message
