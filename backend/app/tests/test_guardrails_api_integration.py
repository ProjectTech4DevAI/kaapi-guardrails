import pytest

pytestmark = pytest.mark.integration

request_id = "123e4567-e89b-12d3-a456-426614174000"

@pytest.mark.integration
def test_input_guardrails_with_real_banlist(integration_client):
    response = integration_client.post(
        "/api/v1/guardrails/input/",
        json={
            "request_id": request_id,
            "input": "this contains badword",
            "validators": [
                {
                    "type": "ban_list",
                    "banned_words": ["badword"]
                }
            ],
        },
    )

    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    assert body["data"]["safe_input"] == "this contains b"

@pytest.mark.integration
def test_input_guardrails_passes_clean_text(integration_client):
    response = integration_client.post(
        "/api/v1/guardrails/input/",
        json={
            "request_id": request_id,
            "input": "this is clean",
            "validators": [
                {
                    "type": "ban_list",
                    "banned_words": ["badword"]
                }
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["success"] is True
    assert body["data"]["safe_input"] == "this is clean"

def test_input_guardrails_with_lexical_slur(integration_client):
    response = integration_client.post(
        "/api/v1/guardrails/input/",
        json={
            "request_id": request_id,
            "input": "This sentence contains chakki.",
            "validators": [
                {
                    "type": "uli_slur_match",
                    "severity": "all",
                }
            ],
        },
    )

    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    assert body["data"]["safe_input"] == "this sentence contains [REDACTED_SLUR]"

def test_input_guardrails_with_lexical_slur_clean_text(integration_client):
    response = integration_client.post(
        "/api/v1/guardrails/input/",
        json={
            "request_id": request_id,
            "input": "This is a completely safe sentence",
            "validators": [
                {
                    "type": "uli_slur_match",
                    "severity": "all",                
                }
            ],
        },
    )

    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    assert body["data"]["safe_input"] == "This is a completely safe sentence"

def test_input_guardrails_with_multiple_validators(integration_client):
    response = integration_client.post(
        "/api/v1/guardrails/input/",
        json={
            "request_id": request_id,
            "input": "This sentence contains chakki cause I want a sonography done to kill the female foetus.",
            "validators": [
                {
                    "type": "uli_slur_match",
                    "severity": "all",
                },
                {
                    "type": "ban_list",
                    "banned_words": ["sonography"]
                }
            ],
        },
    )

    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    assert body["data"]["safe_input"] == "this sentence contains [REDACTED_SLUR] cause i want a s done to kill the female foetus"

def test_input_guardrails_with_incorrect_validator_config(integration_client):
    response = integration_client.post(
        "/api/v1/guardrails/input/",
        json={
            "request_id": request_id,
            "input": "This sentence contains chakki.",
            "validators": [
                {
                    "type": "lexical_slur",
                    "severity": "all",  # Invalid severity
                }
            ],
        },
    )

    assert response.status_code == 422

    body = response.json()
    assert body["success"] is False
    assert "lexical_slur" in body["error"]
    assert "does not match any of the expected tags" in body["error"]

def test_input_guardrails_with_validator_actions(integration_client):
    response = integration_client.post(
        "/api/v1/guardrails/input/",
        json={
            "request_id": request_id,
            "input": "This sentence contains chakki.",
            "validators": [
                {
                    "type": "uli_slur_match",
                    "severity": "all",
                    "on_fail": "exception"
                }
            ],
        },
    )

    assert response.status_code == 500

    body = response.json()
    assert body["success"] is False
    assert body["error"]["type"] == "config_error"
    assert body["error"]["reason"] == "Validation failed for field with errors: Mentioned toxic words: chakki"