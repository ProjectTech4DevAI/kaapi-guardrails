import json
import logging
import uuid
from uuid import UUID

from fastapi import APIRouter, HTTPException
from guardrails.guard import Guard
from guardrails.validators import FailResult, PassResult
from sqlmodel import Session

from app.api.deps import AuthDep, SessionDep, TenantContext
from app.core.constants import (
    BAN_LIST,
    LLM_CRITIC_ERROR_MESSAGE,
    LLM_CRITIC_REPHRASE_MESSAGE,
    REPHRASE_ON_FAIL_PREFIX,
)
from app.core.enum import LLMValidatorName, Stage, ValidatorType
from app.core.exception_handlers import _normalize_error_detail, _safe_error_message
from app.core.guardrail_controller import build_guard, get_validator_config_models
from app.core.validators.config.answer_relevance_custom_llm_safety_validator_config import (
    AnswerRelevanceCustomLLMSafetyValidatorConfig,
)
from app.core.validators.config.ban_list_safety_validator_config import (
    BanListSafetyValidatorConfig,
)
from app.core.validators.config.topic_relevance_llm_safety_validator_config import (
    TopicRelevanceLLMSafetyValidatorConfig,
)
from app.core.validators.config.topic_relevance_safety_validator_config import (
    TopicRelevanceSafetyValidatorConfig,
)
from app.crud.ban_list import ban_list_crud
from app.crud.llm_prompt_config import llm_prompt_config_crud
from app.crud.request_log import RequestLogCrud
from app.crud.validator_log import ValidatorLogCrud
from app.models.logging.request_log import RequestLogUpdate, RequestStatus
from app.models.logging.validator_log import ValidatorLog, ValidatorOutcome
from app.schemas.guardrail_config import (
    GuardrailRequest,
    GuardrailResponse,
    ValidatorConfigItem,
)
from app.utils import APIResponse, load_description

logger = logging.getLogger(__name__)

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
    auth: AuthDep,
    suppress_pass_logs: bool = False,
):
    """
    Resolves any config-backed validator references (ban list words, topic relevance scope),
    then runs validation and returns a structured guardrail response.
    """
    request_log_crud = RequestLogCrud(session=session)
    validator_log_crud = ValidatorLogCrud(session=session)

    try:
        request_log = request_log_crud.create(
            payload, auth.organization_id, auth.project_id, suppress_pass_logs
        )
    except ValueError:
        logger.warning(
            "[run_guardrails] invalid request_id %r (org=%s project=%s), no request log written",
            payload.request_id,
            auth.organization_id,
            auth.project_id,
        )
        return APIResponse.failure_response(error="Invalid request_id")

    try:
        _resolve_validator_configs(payload, session, auth)
    except Exception as exc:
        # Config resolution failed (missing/mismatched stored config, DB error).
        # Finalize the request log so it never sits at PROCESSING forever.
        error_message = (
            _normalize_error_detail(exc.detail)
            if isinstance(exc, HTTPException)
            else _safe_error_message(exc)
        )
        if isinstance(error_message, list):
            error_message = "; ".join(str(item) for item in error_message)
        logger.error(
            "[run_guardrails] config resolution failed for request_log %s: %s",
            request_log.id,
            exc,
            exc_info=not isinstance(exc, HTTPException),
        )
        _mark_request_failed(request_log_crud, request_log.id, error_message)
        if isinstance(exc, HTTPException):
            raise
        return APIResponse.failure_response(error=error_message)

    has_output_validator = any(
        isinstance(v, AnswerRelevanceCustomLLMSafetyValidatorConfig)
        for v in payload.validators
    )
    data = (payload.output or "") if has_output_validator else payload.input
    return _validate_with_guard(
        payload,
        data,
        request_log_crud,
        request_log.id,
        validator_log_crud,
        auth,
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


def _mark_request_failed(
    request_log_crud: RequestLogCrud, request_log_id: UUID, error_message: str
) -> None:
    """Best-effort finalization of a request log on an early-exit error path."""
    try:
        # The error that got us here may have left the shared session in a
        # failed-transaction state; clear it or this update raises too.
        request_log_crud.session.rollback()
        request_log_crud.update(
            request_log_id=request_log_id,
            request_status=RequestStatus.ERROR,
            request_log_update=RequestLogUpdate(
                response_text=error_message,
                response_id=uuid.uuid4(),
            ),
        )
    except Exception:
        logger.exception(
            "[_mark_request_failed] failed to finalize request log %s after an error",
            request_log_id,
        )


def _resolve_validator_configs(
    payload: GuardrailRequest, session: Session, auth: TenantContext
) -> None:
    """
    Resolves config-backed references for all validators in-place before guard execution:
    - BanList: fetches banned_words from the stored BanList when not provided inline.
    - TopicRelevance: fetches configuration and prompt_schema_version from stored config.
    - TopicRelevanceLLM: fetches configuration from stored config.
    - AnswerRelevance: fetches custom prompt template from stored config.

    Returns the data string to pass to guard.validate().
    """
    for validator in payload.validators:
        if isinstance(validator, BanListSafetyValidatorConfig):
            if validator.type == BAN_LIST and validator.banned_words is None:
                ban_list = ban_list_crud.get(
                    session,
                    id=validator.ban_list_id,
                    organization_id=auth.organization_id,
                    project_id=auth.project_id,
                )
                validator.banned_words = ban_list.banned_words

        elif isinstance(
            validator,
            (
                TopicRelevanceSafetyValidatorConfig,
                TopicRelevanceLLMSafetyValidatorConfig,
            ),
        ):
            if validator.topic_relevance_config_id is not None:
                config = llm_prompt_config_crud.get(
                    session=session,
                    id=validator.topic_relevance_config_id,
                    organization_id=auth.organization_id,
                    project_id=auth.project_id,
                )
                if config.validator_name != LLMValidatorName.TopicRelevance:
                    raise HTTPException(
                        400,
                        f"LLM prompt config '{config.id}' is for validator "
                        f"'{config.validator_name}', not 'topic_relevance'",
                    )
                validator.configuration = config.llm_prompt
                # Only the LLMCritic-backed variant carries a prompt schema version.
                if isinstance(validator, TopicRelevanceSafetyValidatorConfig):
                    validator.prompt_schema_version = config.prompt_schema_version

        elif isinstance(validator, AnswerRelevanceCustomLLMSafetyValidatorConfig):
            validator.input = payload.input
            validator.output = payload.output or ""
            if validator.custom_prompt_id is not None:
                prompt_config = llm_prompt_config_crud.get(
                    session=session,
                    id=validator.custom_prompt_id,
                    organization_id=auth.organization_id,
                    project_id=auth.project_id,
                )
                if (
                    prompt_config.validator_name
                    != LLMValidatorName.AnswerRelevanceCustomLLM
                ):
                    raise HTTPException(
                        400,
                        f"LLM prompt config '{prompt_config.id}' is for validator "
                        f"'{prompt_config.validator_name}', not 'answer_relevance_custom_llm'",
                    )
                validator.prompt_template = prompt_config.llm_prompt


def _validate_with_guard(
    payload: GuardrailRequest,
    data: str,
    request_log_crud: RequestLogCrud,
    request_log_id: UUID,
    validator_log_crud: ValidatorLogCrud,
    auth: TenantContext,
    suppress_pass_logs: bool = False,
) -> APIResponse:
    """
    Runs Guardrails validation on input/output data, persists request & validator logs,
    and returns a structured APIResponse.

    This function treats validation failures as first-class outcomes (not exceptions),
    while still safely handling unexpected runtime errors.
    """
    response_id = uuid.uuid4()
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

        # Log-persistence failures are logged but never break the user response.
        try:
            request_log_crud.update(
                request_log_id=request_log_id,
                request_status=status,
                request_log_update=RequestLogUpdate(
                    response_text=response_text,
                    response_id=response_id,
                ),
            )
        except Exception:
            logger.exception(
                "[_finalize] failed to update request log %s", request_log_id
            )
            # Clear the failed transaction so the validator-log writes
            # below still have a usable session.
            request_log_crud.session.rollback()

        if guard is not None:
            try:
                add_validator_logs(
                    guard,
                    request_log_id,
                    validator_log_crud,
                    auth,
                    suppress_pass_logs,
                    validator_configs=validators,
                )
            except Exception:
                logger.exception(
                    "[_finalize] failed to write validator logs for request log %s",
                    request_log_id,
                )

        rephrase_needed = validated_output is not None and (
            validated_output == LLM_CRITIC_REPHRASE_MESSAGE
            or validated_output.startswith(REPHRASE_ON_FAIL_PREFIX)
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
        error_message = _extract_error_from_guard(guard, data) or "Validation failed"
        return _finalize(
            status=RequestStatus.ERROR,
            error_message=error_message,
        )

    except Exception as exc:
        logger.error(
            "[_validate_with_guard] guardrails execution failed for request log %s: %s",
            request_log_id,
            exc,
            exc_info=True,
        )
        # Case 3: unexpected system / runtime failure
        # First try to extract structured fail results from guard history.
        # This handles on_fail="exception" where guardrails raises instead of returning.
        if guard is not None:
            extracted = _extract_error_from_guard(guard, data)
            if extracted is not None:
                return _finalize(status=RequestStatus.ERROR, error_message=extracted)

        safe_msg = _redact_input(_safe_error_message(exc), data)
        return _finalize(
            status=RequestStatus.ERROR,
            error_message=safe_msg,
        )


def _extract_error_from_guard(guard: Guard, data: str) -> str | None:
    """
    Scans the guard's last history iteration for the first FailResult and returns
    a normalized, redacted error message. Returns None if no fail result is found.
    """
    history = getattr(guard, "history", None)
    if not history or not getattr(history, "last", None):
        return None
    iterations = getattr(history.last, "iterations", None)
    if not iterations:
        return None
    logs = getattr(getattr(iterations[-1], "outputs", None), "validator_logs", [])
    for log in logs:
        log_result = log.validation_result
        if isinstance(log_result, FailResult) and log_result.error_message:
            if log.validator_name in (
                ValidatorType.LLMCritic.name,
                ValidatorType.LLMCritic.value,
                "LLM_Critic",
            ):
                return _normalize_llm_critic_error(log_result.error_message)
            return _redact_input(log_result.error_message, data)
    return None


def _redact_input(error_message: str, input_text: str) -> str:
    error_message = error_message.split(":\n\n")[0]
    return error_message.replace(input_text, "")


def _map_validator_configs(
    guard: Guard, validator_configs: list[ValidatorConfigItem] | None
) -> dict[str, ValidatorConfigItem]:
    """
    Maps guard-history validator names (rail_alias) back to the request's
    validator configs, using the built validators the guard actually ran.
    """
    built = getattr(guard, "_validators", None)
    if not built or not validator_configs:
        return {}
    # ponytail: first config wins per alias; two same-type validators in one
    # request share trace fields. Split by position if that ever matters.
    mapping: dict[str, ValidatorConfigItem] = {}
    for validator, config in zip(built, validator_configs):
        alias = getattr(validator, "rail_alias", None)
        if alias:
            mapping.setdefault(alias, config)
    return mapping


def add_validator_logs(
    guard: Guard,
    request_log_id: UUID,
    validator_log_crud: ValidatorLogCrud,
    auth: TenantContext,
    suppress_pass_logs: bool = False,
    validator_configs: list[ValidatorConfigItem] | None = None,
) -> None:
    """
    Writes a ValidatorLog entry for each validator outcome in the guard's last iteration.
    Pass results are skipped when suppress_pass_logs is True; `order` keeps each
    row's true execution position, so persisted orders may have gaps — intentional.
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

    config_by_alias = _map_validator_configs(guard, validator_configs)

    for order, log in enumerate(iteration.outputs.validator_logs, start=1):
        result = log.validation_result

        if result is None:
            continue

        if suppress_pass_logs and isinstance(result, PassResult):
            continue

        error_message = None
        if isinstance(result, FailResult):
            error_message = result.error_message

        # registered_name is the rail alias ("guardrails/ban_list");
        # validator_name is only the display/class name.
        config = config_by_alias.get(
            getattr(log, "registered_name", None) or log.validator_name
        )
        stage = type_ = meta = None
        if config is not None:
            type_ = config.type
            # Per-config stage defaults live on the config classes
            # (answer_relevance defaults to output).
            stage = config.stage.value if config.stage else Stage.Input.value
            meta = config.model_dump(mode="json")

        # Verdict detail the validator attached to its result (e.g. topic
        # relevance scope_score/reasoning); stored beside the config dump.
        result_metadata = getattr(result, "metadata", None)
        if result_metadata:
            meta = meta or {}
            # Round-trip through json so a non-serializable value degrades to
            # its str() instead of failing the row insert.
            meta["result_metadata"] = json.loads(
                json.dumps(result_metadata, default=str)
            )

        duration_ms = None
        start_time = getattr(log, "start_time", None)
        end_time = getattr(log, "end_time", None)
        if start_time and end_time:
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

        validator_log = ValidatorLog(
            request_id=request_log_id,
            organization_id=auth.organization_id,
            project_id=auth.project_id,
            name=log.validator_name,
            order=order,
            duration_ms=duration_ms,
            stage=stage,
            type=type_,
            meta=meta,
            input=str(log.value_before_validation),
            output=log.value_after_validation,
            error=error_message,
            outcome=ValidatorOutcome(result.outcome.upper()),
        )

        try:
            validator_log_crud.create(log=validator_log)
        except Exception:
            logger.exception(
                "[add_validator_logs] failed to write validator log (validator=%s, request_log=%s)",
                log.validator_name,
                request_log_id,
            )
            # Clear the failed transaction so one bad row doesn't poison
            # the inserts for the remaining validators.
            validator_log_crud.session.rollback()


def _normalize_llm_critic_error(message: str) -> str:
    if (
        "failed the following metrics" in message
        or "missing or has invalid evaluations" in message
    ):
        return LLM_CRITIC_ERROR_MESSAGE
    return message
