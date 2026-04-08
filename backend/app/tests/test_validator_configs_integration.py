import uuid

import pytest
from app.tests.seed.seed_data import (
    VALIDATOR_INTEGRATION_ORGANIZATION_ID,
    VALIDATOR_INTEGRATION_PROJECT_ID,
    VALIDATOR_PAYLOADS,
)

pytestmark = pytest.mark.integration

BASE_URL = "/api/v1/guardrails/validators/configs/"
DEFAULT_QUERY_PARAMS = (
    f"?organization_id={VALIDATOR_INTEGRATION_ORGANIZATION_ID}"
    f"&project_id={VALIDATOR_INTEGRATION_PROJECT_ID}"
)


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
            f"?organization_id={VALIDATOR_INTEGRATION_ORGANIZATION_ID}"
            f"&project_id={VALIDATOR_INTEGRATION_PROJECT_ID}"
        )
        if query_params:
            params_str += "&" + "&".join(f"{k}={v}" for k, v in query_params.items())
        return client.get(f"{BASE_URL}{params_str}")

    def update_validator(self, client, validator_id, payload):
        """Helper to update a validator."""
        return client.patch(
            f"{BASE_URL}{validator_id}/{DEFAULT_QUERY_PARAMS}", json=payload
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

    def test_create_multiple_validators_success(
        self, integration_client, clear_database
    ):
        """Test creating multiple validators and verifying they're all stored."""
        # Create multiple validators with different configs
        validators_to_create = [
            ("lexical_slur", "uli_slur_match", "lexical_slur_config"),
            ("pii_remover_input", "pii_remover", "pii_remover_input_config"),
            ("pii_remover_output", "pii_remover", "pii_remover_output_config"),
            ("minimal", "gender_assumption_bias", "minimal_config"),
        ]

        created_validators = []

        # Create all validators
        for payload_key, expected_type, expected_name in validators_to_create:
            response = self.create_validator(integration_client, payload_key)
            assert response.status_code == 200
            data = response.json()["data"]
            assert data["type"] == expected_type
            assert data["name"] == expected_name
            assert "id" in data
            created_validators.append(
                {"id": data["id"], "name": expected_name, "type": expected_type}
            )

        # Verify all validators are in the database
        list_response = self.list_validators(integration_client)
        assert list_response.status_code == 200

        all_validators = list_response.json()["data"]
        assert len(all_validators) == 4

        # Verify all created IDs are present
        retrieved_ids = {v["id"] for v in all_validators}
        created_ids = {v["id"] for v in created_validators}
        assert created_ids == retrieved_ids

        # Verify each validator can be retrieved individually with correct name
        for validator in created_validators:
            get_response = self.get_validator(integration_client, validator["id"])
            assert get_response.status_code == 200
            response_data = get_response.json()["data"]
            assert response_data["id"] == validator["id"]
            assert response_data["name"] == validator["name"]
            assert response_data["type"] == validator["type"]

    def test_create_and_update_multiple_validators(
        self, integration_client, clear_database
    ):
        """Test creating multiple validators, then updating each one."""
        # Create three validators
        validator1 = self.create_validator(integration_client, "lexical_slur")
        validator2 = self.create_validator(integration_client, "pii_remover_input")
        validator3 = self.create_validator(integration_client, "minimal")

        assert validator1.status_code == 200
        assert validator2.status_code == 200
        assert validator3.status_code == 200

        id1 = validator1.json()["data"]["id"]
        id2 = validator2.json()["data"]["id"]
        id3 = validator3.json()["data"]["id"]

        # Update all three validators with different settings including name
        update1 = self.update_validator(
            integration_client,
            id1,
            {"is_enabled": False, "name": "updated_slur_config"},
        )
        update2 = self.update_validator(
            integration_client,
            id2,
            {"on_fail_action": "exception", "name": "updated_pii_config"},
        )
        update3 = self.update_validator(
            integration_client,
            id3,
            {
                "is_enabled": False,
                "on_fail_action": "rephrase",
                "name": "updated_minimal_config",
            },
        )

        assert update1.status_code == 200
        assert update2.status_code == 200
        assert update3.status_code == 200

        # Verify updates persisted
        assert update1.json()["data"]["is_enabled"] is False
        assert update1.json()["data"]["name"] == "updated_slur_config"
        assert update2.json()["data"]["on_fail_action"] == "exception"
        assert update2.json()["data"]["name"] == "updated_pii_config"
        assert update3.json()["data"]["is_enabled"] is False
        assert update3.json()["data"]["on_fail_action"] == "rephrase"
        assert update3.json()["data"]["name"] == "updated_minimal_config"

        # Verify all three are still in the database with updated names
        list_response = self.list_validators(integration_client)
        all_validators = list_response.json()["data"]
        assert len(all_validators) == 3

        validator_names = {v["name"] for v in all_validators}
        assert validator_names == {
            "updated_slur_config",
            "updated_pii_config",
            "updated_minimal_config",
        }


class TestListValidators(BaseValidatorTest):
    """Tests for GET /guardrails/validators/configs endpoint."""

    def test_list_validators_success(self, integration_client, seed_db):
        """Test successful validator listing."""

        response = self.list_validators(integration_client)

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 4

    def test_list_validators_filter_by_stage(self, integration_client, seed_db):
        """Test filtering validators by stage."""

        response = self.list_validators(integration_client, stage="input")

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 3
        assert data[0]["stage"] == "input"

    def test_list_validators_filter_by_type(self, integration_client, seed_db):
        """Test filtering validators by type."""

        response = self.list_validators(integration_client, type="pii_remover")

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 2
        assert data[0]["type"] == "pii_remover"

    def test_list_validators_filter_by_ids(self, integration_client, clear_database):
        """Test filtering validators by ids query parameter."""
        first = self.create_validator(integration_client, "lexical_slur")
        second = self.create_validator(integration_client, "pii_remover_input")
        first_id = first.json()["data"]["id"]
        second_id = second.json()["data"]["id"]

        response = integration_client.get(
            f"{BASE_URL}{DEFAULT_QUERY_PARAMS}&ids={first_id}",
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 1
        assert data[0]["id"] == first_id
        assert data[0]["id"] != second_id

    def test_list_validators_filter_by_multiple_ids(
        self, integration_client, clear_database
    ):
        """Test filtering validators by multiple ids query parameters."""
        first = self.create_validator(integration_client, "lexical_slur")
        second = self.create_validator(integration_client, "pii_remover_input")
        first_id = first.json()["data"]["id"]
        second_id = second.json()["data"]["id"]

        response = integration_client.get(
            f"{BASE_URL}{DEFAULT_QUERY_PARAMS}&ids={first_id}&ids={second_id}",
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 2
        returned_ids = {item["id"] for item in data}
        assert returned_ids == {first_id, second_id}

    def test_list_validators_invalid_ids_query_returns_422(
        self, integration_client, clear_database
    ):
        """Test invalid UUID in ids query returns validation error."""
        response = integration_client.get(
            f"{BASE_URL}{DEFAULT_QUERY_PARAMS}&ids=not-a-uuid",
        )

        assert response.status_code == 422

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

    def test_get_validator_success(self, integration_client, seed_db):
        """Test successful validator retrieval."""
        list_response = self.list_validators(integration_client)
        validator_id = list_response.json()["data"][0]["id"]

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

    def test_get_validator_invalid_id_returns_422(
        self, integration_client, clear_database
    ):
        """Test invalid UUID path param returns validation error."""
        response = integration_client.get(
            f"{BASE_URL}not-a-uuid/{DEFAULT_QUERY_PARAMS}",
        )

        assert response.status_code == 422

    def test_get_validator_wrong_org(self, integration_client, clear_database):
        """Test that accessing validator from different org returns 404."""
        create_response = self.create_validator(integration_client, "minimal")
        validator_id = create_response.json()["data"]["id"]

        # Try to access it as different org
        response = integration_client.get(
            f"{BASE_URL}{validator_id}/?organization_id=2&project_id=1",
        )

        assert response.status_code == 404


class TestUpdateValidator(BaseValidatorTest):
    """Tests for PATCH /guardrails/validators/configs/{id} endpoint."""

    def test_update_validator_success(self, integration_client, seed_db):
        """Test successful validator update."""
        list_response = self.list_validators(integration_client)
        validator_id = list_response.json()["data"][0]["id"]

        # Update it
        update_payload = {"on_fail_action": "exception", "is_enabled": False}
        response = self.update_validator(
            integration_client, validator_id, update_payload
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["on_fail_action"] == "exception"
        assert data["is_enabled"] is False

    def test_update_validator_partial(self, integration_client, seed_db):
        """Test partial update preserves original fields."""
        list_response = self.list_validators(integration_client)
        validator_id = list_response.json()["data"][0]["id"]

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

    def test_delete_validator_success(self, integration_client, seed_db):
        """Test successful validator deletion."""
        list_response = self.list_validators(integration_client)
        validator_id = list_response.json()["data"][0]["id"]

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

    def test_delete_validator_wrong_org(self, integration_client, seed_db):
        """Test that deleting validator from different org returns 404."""
        list_response = self.list_validators(integration_client)
        validator_id = list_response.json()["data"][0]["id"]

        # Try to delete it as different org
        response = integration_client.delete(
            f"{BASE_URL}{validator_id}/?organization_id=2&project_id=1",
        )

        assert response.status_code == 404

        # Verify original is still there
        get_response = self.get_validator(integration_client, validator_id)
        assert get_response.status_code == 200
