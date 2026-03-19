from unittest.mock import MagicMock, patch
from uuid import uuid4

from guardrails.validators import FailResult as GRFailResult

from app.api.routes.guardrails import (
    _resolve_validator_configs,
    _validate_with_guard,
)
from app.schemas.guardrail_config import GuardrailRequest
from app.tests.guardrails_mocks import MockResult
from app.tests.seed_data import (
    VALIDATOR_TEST_ORGANIZATION_ID,
    VALIDATOR_TEST_PROJECT_ID,
)
from app.utils import APIResponse

mock_request_log_crud = MagicMock()
mock_validator_log_crud = MagicMock()
mock_request_log_id = uuid4()


def _build_payload(input_text: str) -> GuardrailRequest:
    return GuardrailRequest(
        request_id=str(uuid4()),
        organization_id=VALIDATOR_TEST_ORGANIZATION_ID,
        project_id=VALIDATOR_TEST_PROJECT_ID,
        input=input_text,
        validators=[],
    )


def test_validate_with_guard_success():
    class MockGuard:
        def validate(self, data):
            return MockResult(validated_output="clean text")

    with patch(
        "app.api.routes.guardrails.build_guard",
        return_value=MockGuard(),
    ):
        response = _validate_with_guard(
            payload=_build_payload("hello"),
            request_log_crud=mock_request_log_crud,
            request_log_id=mock_request_log_id,
            validator_log_crud=mock_validator_log_crud,
        )

    assert isinstance(response, APIResponse)
    assert response.success is True
    assert response.data.safe_text == "clean text"
    assert response.data.response_id is not None


def test_validate_with_guard_validation_error():
    class MockGuard:
        def validate(self, data):
            return MockResult(validated_output=None)

    with patch(
        "app.api.routes.guardrails.build_guard",
        return_value=MockGuard(),
    ):
        response = _validate_with_guard(
            payload=_build_payload("bad text"),
            request_log_crud=mock_request_log_crud,
            request_log_id=mock_request_log_id,
            validator_log_crud=mock_validator_log_crud,
        )

    assert isinstance(response, APIResponse)
    assert response.success is False
    assert response.data.safe_text is None
    assert response.error


def test_validate_with_guard_exception():
    with patch(
        "app.api.routes.guardrails.build_guard",
        side_effect=Exception("Invalid config"),
    ):
        response = _validate_with_guard(
            payload=_build_payload("text"),
            request_log_crud=mock_request_log_crud,
            request_log_id=mock_request_log_id,
            validator_log_crud=mock_validator_log_crud,
        )

    assert isinstance(response, APIResponse)
    assert response.success is False
    assert response.data.safe_text is None
    assert response.error == "Invalid config"


def test_validate_with_guard_uses_fail_result_error_message():
    """Case 2: when guard returns no validated_output, the error message should
    be extracted from the first FailResult in the last iteration's validator logs."""
    mock_log = MagicMock()
    mock_log.validation_result = GRFailResult(error_message="specific validator error")

    mock_outputs = MagicMock()
    mock_outputs.validator_logs = [mock_log]

    mock_iteration = MagicMock()
    mock_iteration.outputs = mock_outputs

    mock_last = MagicMock()
    mock_last.iterations = [mock_iteration]

    mock_history = MagicMock()
    mock_history.last = mock_last

    class MockGuard:
        history = mock_history

        def validate(self, data):
            return MockResult(validated_output=None)

    with patch(
        "app.api.routes.guardrails.build_guard", return_value=MockGuard()
    ), patch("app.api.routes.guardrails.add_validator_logs"):
        response = _validate_with_guard(
            payload=_build_payload("bad text"),
            request_log_crud=mock_request_log_crud,
            request_log_id=mock_request_log_id,
            validator_log_crud=mock_validator_log_crud,
        )

    assert response.success is False
    assert response.error == "specific validator error"


def test_validate_with_guard_handles_empty_iterations():
    """Case 2: when guard history exists but iterations is empty, falls back
    to the default 'Validation failed' message without raising."""

    class MockGuard:
        class history:
            class last:
                iterations = []

        def validate(self, data):
            return MockResult(validated_output=None)

    with patch(
        "app.api.routes.guardrails.build_guard",
        return_value=MockGuard(),
    ):
        response = _validate_with_guard(
            payload=_build_payload("bad text"),
            request_log_crud=mock_request_log_crud,
            request_log_id=mock_request_log_id,
            validator_log_crud=mock_validator_log_crud,
        )

    assert response.success is False
    assert response.error == "Validation failed"


def test_resolve_validator_configs_ban_list_from_id():
    ban_list_id = str(uuid4())
    payload = GuardrailRequest(
        request_id=str(uuid4()),
        organization_id=VALIDATOR_TEST_ORGANIZATION_ID,
        project_id=VALIDATOR_TEST_PROJECT_ID,
        input="test",
        validators=[{"type": "ban_list", "ban_list_id": ban_list_id}],
    )
    mock_session = MagicMock()

    with patch("app.api.routes.guardrails.ban_list_crud.get") as mock_get:
        mock_get.return_value = MagicMock(banned_words=["foo", "bar"])
        _resolve_validator_configs(payload, mock_session)

    assert payload.validators[0].banned_words == ["foo", "bar"]
    mock_get.assert_called_once_with(
        mock_session,
        id=payload.validators[0].ban_list_id,
        organization_id=VALIDATOR_TEST_ORGANIZATION_ID,
        project_id=VALIDATOR_TEST_PROJECT_ID,
    )


def test_resolve_validator_configs_skips_ban_list_lookup_when_words_provided():
    payload = GuardrailRequest(
        request_id=str(uuid4()),
        organization_id=VALIDATOR_TEST_ORGANIZATION_ID,
        project_id=VALIDATOR_TEST_PROJECT_ID,
        input="test",
        validators=[
            {"type": "ban_list", "ban_list_id": str(uuid4()), "banned_words": ["foo"]}
        ],
    )
    mock_session = MagicMock()

    with patch("app.api.routes.guardrails.ban_list_crud.get") as mock_get:
        _resolve_validator_configs(payload, mock_session)

    mock_get.assert_not_called()


def test_resolve_validator_configs_topic_relevance_from_config_id():
    topic_relevance_id = str(uuid4())
    payload = GuardrailRequest(
        request_id=str(uuid4()),
        organization_id=VALIDATOR_TEST_ORGANIZATION_ID,
        project_id=VALIDATOR_TEST_PROJECT_ID,
        input="test",
        validators=[
            {"type": "topic_relevance", "topic_relevance_config_id": topic_relevance_id}
        ],
    )
    mock_session = MagicMock()

    with patch("app.api.routes.guardrails.topic_relevance_crud.get") as mock_get:
        mock_get.return_value = MagicMock(
            configuration="Topic scope prompt text",
            prompt_schema_version=2,
        )
        _resolve_validator_configs(payload, mock_session)

    validator = payload.validators[0]
    assert validator.configuration == "Topic scope prompt text"
    assert validator.prompt_schema_version == 2
    mock_get.assert_called_once_with(
        session=mock_session,
        id=validator.topic_relevance_config_id,
        organization_id=VALIDATOR_TEST_ORGANIZATION_ID,
        project_id=VALIDATOR_TEST_PROJECT_ID,
    )


def test_resolve_validator_configs_skips_topic_relevance_lookup_when_no_config_id():
    payload = GuardrailRequest(
        request_id=str(uuid4()),
        organization_id=VALIDATOR_TEST_ORGANIZATION_ID,
        project_id=VALIDATOR_TEST_PROJECT_ID,
        input="test",
        validators=[{"type": "topic_relevance"}],
    )
    mock_session = MagicMock()

    with patch("app.api.routes.guardrails.topic_relevance_crud.get") as mock_get:
        _resolve_validator_configs(payload, mock_session)

    mock_get.assert_not_called()


def test_resolve_validator_configs_uses_inline_topic_relevance_without_lookup():
    payload = GuardrailRequest(
        request_id=str(uuid4()),
        organization_id=VALIDATOR_TEST_ORGANIZATION_ID,
        project_id=VALIDATOR_TEST_PROJECT_ID,
        input="test",
        validators=[
            {
                "type": "topic_relevance",
                "configuration": "inline config",
            }
        ],
    )
    mock_session = MagicMock()

    with patch("app.api.routes.guardrails.topic_relevance_crud.get") as mock_get:
        _resolve_validator_configs(payload, mock_session)

    validator = payload.validators[0]
    assert validator.configuration == "inline config"
    mock_get.assert_not_called()
