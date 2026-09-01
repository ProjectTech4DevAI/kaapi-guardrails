from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import Session, select

from app.models.logging.request_log import RequestLog, RequestStatus
from app.models.logging.validator_log import ValidatorLog
from app.tests.conftest import test_engine
from app.tests.seed_data import (
    VALIDATOR_INTEGRATION_ORGANIZATION_ID,
    VALIDATOR_INTEGRATION_PROJECT_ID,
)
from app.tests.utils.constants import VALIDATE_API_PATH

pytestmark = pytest.mark.integration

request_id = "123e4567-e89b-12d3-a456-426614174000"
TENANT_HEADERS = {
    "X-ORGANIZATION-ID": str(VALIDATOR_INTEGRATION_ORGANIZATION_ID),
    "X-PROJECT-ID": str(VALIDATOR_INTEGRATION_PROJECT_ID),
}


def test_validator_logs_capture_order_stage_type_family_and_metadata(
    integration_client,
):
    payload = {
        "request_id": request_id,
        "input": "this contains badword",
        "validators": [
            {"type": "ban_list", "banned_words": ["badword"], "stage": "input"},
            {"type": "uli_slur_match", "severity": "all"},
        ],
    }
    response = integration_client.post(
        VALIDATE_API_PATH, headers=TENANT_HEADERS, json=payload
    )
    assert response.status_code == 200
    assert response.json()["success"] is True

    with Session(test_engine) as session:
        request_log = session.exec(select(RequestLog)).one()
        assert request_log.status == RequestStatus.SUCCESS
        # Metadata is the parsed payload with validator defaults filled in.
        assert request_log.meta["request_id"] == request_id
        assert request_log.meta["input"] == payload["input"]
        assert [v["type"] for v in request_log.meta["validators"]] == [
            "ban_list",
            "uli_slur_match",
        ]

        logs = session.exec(select(ValidatorLog).order_by(ValidatorLog.order)).all()
        # Passing validators are logged by default (suppress_pass_logs=False).
        assert [log.order for log in logs] == [1, 2]
        assert [log.type for log in logs] == ["ban_list", "uli_slur_match"]
        assert [log.family for log in logs] == ["lexical", "lexical"]
        assert [log.stage for log in logs] == ["input", "input"]
        assert logs[0].meta["banned_words"] == ["badword"]
        assert logs[0].meta["stage"] == "input"
        assert logs[1].meta["type"] == "uli_slur_match"


def test_config_resolution_failure_finalizes_request_log(integration_client):
    response = integration_client.post(
        VALIDATE_API_PATH,
        headers=TENANT_HEADERS,
        json={
            "request_id": request_id,
            "input": "hello",
            "validators": [
                {
                    "type": "ban_list",
                    "ban_list_id": "00000000-0000-0000-0000-000000000000",
                }
            ],
        },
    )
    assert response.status_code == 404

    with Session(test_engine) as session:
        request_log = session.exec(select(RequestLog)).one()
        # The row must not be left at PROCESSING forever.
        assert request_log.status == RequestStatus.ERROR
        assert request_log.response_text


def test_guard_execution_failure_finalizes_request_log(integration_client):
    failing_guard = MagicMock()
    failing_guard.validate.side_effect = RuntimeError("boom")
    failing_guard.history = None  # no structured fail results to extract

    with patch("app.api.routes.guardrails.build_guard", return_value=failing_guard):
        response = integration_client.post(
            VALIDATE_API_PATH,
            headers=TENANT_HEADERS,
            json={
                "request_id": request_id,
                "input": "hello",
                "validators": [{"type": "ban_list", "banned_words": ["x"]}],
            },
        )

    # The failure is a first-class outcome, not an exception to the caller.
    assert response.status_code == 200
    assert response.json()["success"] is False

    with Session(test_engine) as session:
        request_log = session.exec(select(RequestLog)).one()
        assert request_log.status == RequestStatus.ERROR
        assert request_log.response_text


def test_invalid_request_id_returns_failure_without_crash(integration_client):
    response = integration_client.post(
        VALIDATE_API_PATH,
        headers=TENANT_HEADERS,
        json={
            "request_id": "not-a-uuid",
            "input": "hello",
            "validators": [{"type": "ban_list", "banned_words": ["x"]}],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert body["error"] == "Invalid request_id"
