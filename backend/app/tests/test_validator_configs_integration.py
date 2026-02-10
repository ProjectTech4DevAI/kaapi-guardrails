import uuid

import pytest
from sqlmodel import Session, delete

from app.core.db import engine
from app.models.config.validator_config import ValidatorConfig

pytestmark = pytest.mark.integration

# Test data constants
TEST_ORGANIZATION_ID = 1
TEST_PROJECT_ID = 1
BASE_URL = "/api/v1/guardrails/validators/configs/"
DEFAULT_QUERY_PARAMS = (
    f"?organization_id={TEST_ORGANIZATION_ID}&project_id={TEST_PROJECT_ID}"
)

VALIDATOR_PAYLOADS = {
    "lexical_slur": {
        "type": "uli_slur_match",
        "stage": "input",
        "on_fail_action": "fix",
        "severity": "all",
        "languages": ["en", "hi"],
    },
    "pii_remover_input": {
        "type": "pii_remover",
        "stage": "input",
        "on_fail_action": "fix",
    },
    "pii_remover_output": {
        "type": "pii_remover",
        "stage": "output",
        "on_fail_action": "fix",
    },
    "minimal": {
        "type": "uli_slur_match",
        "stage": "input",
        "on_fail_action": "fix",
    },
}


@pytest.fixture
def clear_database():
    """Clear ValidatorConfig table before and after each test."""
    with Session(engine) as session:
        session.exec(delete(ValidatorConfig))
        session.commit()

    yield

    with Session(engine) as session:
        session.exec(delete(ValidatorConfig))
        session.commit()


class BaseValidatorTest:
    """Base class with helper methods for validator tests."""

    def create_validator(self, client, payload_key="minimal", **kwargs):
        """Helper to create a validator."""
        payload = {**VALIDATOR_PAYLOADS[payload_key], **kwargs}
        return client.post(f"{BASE_URL}{DEFAULT_QUERY_PARAMS}", json=payload)

    def get_validator(self, client, validator_id):
        """Helper to get a specific validator."""
        return client.get(f"{BASE_URL}{validator_id}/{DEFAULT_QUERY_PARAMS}")

    def list_validators(self, client, **query_params):
        """Helper to list validators with optional filters."""
        params_str = (
            f"?organization_id={TEST_ORGANIZATION_ID}&project_id={TEST_PROJECT_ID}"
        )
        if query_params:
            params_str += "&" + "&".join(f"{k}={v}" for k, v in query_params.items())
        return client.get(f"{BASE_URL}{params_str}")

    def update_validator(self, client, validator_id, payload):
        """Helper to update a validator."""
        return client.patch(
            f"{BASE_URL}{validator_id}{DEFAULT_QUERY_PARAMS}", json=payload
        )

    def delete_validator(self, client, validator_id):
        """Helper to delete a validator."""
        return client.delete(f"{BASE_URL}{validator_id}/{DEFAULT_QUERY_PARAMS}")


class TestCreateValidator(BaseValidatorTest):
    """Tests for POST /guardrails/validators/configs endpoint."""

    def test_create_validator_success(self, integration_client, clear_database):
        """Test successful validator creation."""
        response = self.create_validator(integration_client, "lexical_slur")

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["type"] == "uli_slur_match"
        assert data["stage"] == "input"
        assert data["severity"] == "all"
        assert data["languages"] == ["en", "hi"]
        assert "id" in data

    def test_create_validator_duplicate_raises_400(
        self, integration_client, clear_database
    ):
        """Test that creating duplicate validator raises 400."""
        # First request should succeed
        response1 = self.create_validator(integration_client, "minimal")
        assert response1.status_code == 200

        # Second request with same unique keys should fail
        response2 = self.create_validator(integration_client, "minimal")
        assert response2.status_code == 400

    def test_create_validator_missing_required_fields(
        self, integration_client, clear_database
    ):
        """Test that missing required fields returns validation error."""
        response = integration_client.post(
            f"{BASE_URL}{DEFAULT_QUERY_PARAMS}",
            json={"type": "uli_slur_match"},
        )

        assert response.status_code == 422


class TestListValidators(BaseValidatorTest):
    """Tests for GET /guardrails/validators/configs endpoint."""

    def test_list_validators_success(self, integration_client, clear_database):
        """Test successful validator listing."""
        # Create validators first
        self.create_validator(integration_client, "lexical_slur")
        self.create_validator(integration_client, "pii_remover_input")

        response = self.list_validators(integration_client)

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 2

    def test_list_validators_filter_by_stage(self, integration_client, clear_database):
        """Test filtering validators by stage."""
        self.create_validator(integration_client, "lexical_slur")
        self.create_validator(integration_client, "pii_remover_output")

        response = self.list_validators(integration_client, stage="input")

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 1
        assert data[0]["stage"] == "input"

    def test_list_validators_filter_by_type(self, integration_client, clear_database):
        """Test filtering validators by type."""
        self.create_validator(integration_client, "lexical_slur")
        self.create_validator(integration_client, "pii_remover_input")

        response = self.list_validators(integration_client, type="pii_remover")

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 1
        assert data[0]["type"] == "pii_remover"

    def test_list_validators_empty(self, integration_client, clear_database):
        """Test listing validators when none exist."""
        response = integration_client.get(
            f"{BASE_URL}?organization_id=999&project_id=999",
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 0


class TestGetValidator(BaseValidatorTest):
    """Tests for GET /guardrails/validators/configs/{id} endpoint."""

    def test_get_validator_success(self, integration_client, clear_database):
        """Test successful validator retrieval."""
        # Create a validator
        create_response = self.create_validator(
            integration_client, "lexical_slur", severity="all"
        )
        validator_id = create_response.json()["data"]["id"]

        # Retrieve it
        response = self.get_validator(integration_client, validator_id)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["id"] == validator_id
        assert data["severity"] == "all"

    def test_get_validator_not_found(self, integration_client, clear_database):
        """Test retrieving non-existent validator returns 404."""
        fake_id = uuid.uuid4()
        response = self.get_validator(integration_client, fake_id)

        assert response.status_code == 404

    def test_get_validator_wrong_org(self, integration_client, clear_database):
        """Test that accessing validator from different org returns 404."""
        # Create a validator for org 1
        create_response = self.create_validator(integration_client, "minimal")
        validator_id = create_response.json()["data"]["id"]

        # Try to access it as different org
        response = integration_client.get(
            f"{BASE_URL}{validator_id}/?organization_id=2&project_id=1",
        )

        assert response.status_code == 404


class TestUpdateValidator(BaseValidatorTest):
    """Tests for PATCH /guardrails/validators/configs/{id} endpoint."""

    def test_update_validator_success(self, integration_client, clear_database):
        """Test successful validator update."""
        # Create a validator
        create_response = self.create_validator(
            integration_client, "lexical_slur", severity="all"
        )
        validator_id = create_response.json()["data"]["id"]

        # Update it
        update_payload = {"on_fail_action": "exception", "is_enabled": False}
        response = self.update_validator(
            integration_client, validator_id, update_payload
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["on_fail_action"] == "exception"
        assert data["is_enabled"] is False

    def test_update_validator_partial(self, integration_client, clear_database):
        """Test partial update preserves original fields."""
        # Create a validator
        create_response = self.create_validator(
            integration_client,
            "lexical_slur",
            severity="all",
            languages=["en", "hi"],
        )
        validator_id = create_response.json()["data"]["id"]

        # Update only one field
        update_payload = {"is_enabled": False}
        response = self.update_validator(
            integration_client, validator_id, update_payload
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["is_enabled"] is False
        assert data["on_fail_action"] == "fix"  # Original preserved

    def test_update_validator_not_found(self, integration_client, clear_database):
        """Test updating non-existent validator returns 404."""
        fake_id = uuid.uuid4()
        update_payload = {"is_enabled": False}

        response = self.update_validator(integration_client, fake_id, update_payload)

        assert response.status_code == 404


class TestDeleteValidator(BaseValidatorTest):
    """Tests for DELETE /guardrails/validators/configs/{id} endpoint."""

    def test_delete_validator_success(self, integration_client, clear_database):
        """Test successful validator deletion."""
        # Create a validator
        create_response = self.create_validator(integration_client, "minimal")
        validator_id = create_response.json()["data"]["id"]

        # Delete it
        response = self.delete_validator(integration_client, validator_id)

        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify it's deleted
        get_response = self.get_validator(integration_client, validator_id)
        assert get_response.status_code == 404

    def test_delete_validator_not_found(self, integration_client, clear_database):
        """Test deleting non-existent validator returns 404."""
        fake_id = uuid.uuid4()
        response = self.delete_validator(integration_client, fake_id)

        assert response.status_code == 404

    def test_delete_validator_wrong_org(self, integration_client, clear_database):
        """Test that deleting validator from different org returns 404."""
        # Create a validator for org 1
        create_response = self.create_validator(integration_client, "minimal")
        validator_id = create_response.json()["data"]["id"]

        # Try to delete it as different org
        response = integration_client.delete(
            f"{BASE_URL}{validator_id}/?organization_id=2&project_id=1",
        )

        assert response.status_code == 404

        # Verify original is still there
        get_response = self.get_validator(integration_client, validator_id)
        assert get_response.status_code == 200
