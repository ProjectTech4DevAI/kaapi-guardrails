from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.api.routes.guardrails import (
    _resolve_ban_list_banned_words,
    _resolve_topic_relevance_scope,
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


def test_resolve_ban_list_banned_words_from_ban_list_id():
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
        _resolve_ban_list_banned_words(payload, mock_session)

    assert payload.validators[0].banned_words == ["foo", "bar"]
    mock_get.assert_called_once_with(
        mock_session,
        id=payload.validators[0].ban_list_id,
        organization_id=VALIDATOR_TEST_ORGANIZATION_ID,
        project_id=VALIDATOR_TEST_PROJECT_ID,
    )


def test_resolve_ban_list_banned_words_skips_lookup_when_banned_words_provided():
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
        _resolve_ban_list_banned_words(payload, mock_session)

    mock_get.assert_not_called()


def test_resolve_topic_relevance_scope_from_config_id():
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
            prompt_version=2,
        )
        _resolve_topic_relevance_scope(payload, mock_session)

    validator = payload.validators[0]
    assert validator.configuration == "Topic scope prompt text"
    assert validator.prompt_version == 2
    mock_get.assert_called_once_with(
        session=mock_session,
        id=validator.topic_relevance_config_id,
        organization_id=VALIDATOR_TEST_ORGANIZATION_ID,
        project_id=VALIDATOR_TEST_PROJECT_ID,
    )


def test_topic_relevance_runtime_payload_allows_missing_config_id():
    payload = GuardrailRequest(
        request_id=str(uuid4()),
        organization_id=VALIDATOR_TEST_ORGANIZATION_ID,
        project_id=VALIDATOR_TEST_PROJECT_ID,
        input="test",
        validators=[{"type": "topic_relevance"}],
    )
    mock_session = MagicMock()

    with patch("app.api.routes.guardrails.topic_relevance_crud.get") as mock_get:
        _resolve_topic_relevance_scope(payload, mock_session)

    mock_get.assert_not_called()


def test_topic_relevance_runtime_payload_allows_inline_configuration_without_lookup():
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
        _resolve_topic_relevance_scope(payload, mock_session)

    validator = payload.validators[0]
    assert validator.configuration == "inline config"
    mock_get.assert_not_called()
