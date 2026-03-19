import uuid

import pytest

from app.schemas.topic_relevance import MAX_TOPIC_RELEVANCE_NAME_LENGTH

pytestmark = pytest.mark.integration

BASE_URL = "/api/v1/guardrails/topic_relevance_configs/"
DEFAULT_API_KEY = "org1_project1"
ALT_API_KEY = "org999_project999"


class BaseTopicRelevanceTest:
    def _headers(self, api_key=DEFAULT_API_KEY):
        return {"X-API-Key": api_key}

    def create(self, client, api_key=DEFAULT_API_KEY, **kwargs):
        name = kwargs.get("name", "Maternal Health Scope")
        payload = {
            "name": name,
            "description": "Topic guard for maternal health support bot",
            "prompt_schema_version": 1,
            "configuration": (
                "Pregnancy care: Questions about prenatal care, supplements, and "
                "danger signs. Postpartum care: Questions about recovery after "
                f"delivery and breastfeeding. Scope name: {name}."
            ),
            **kwargs,
        }
        return client.post(BASE_URL, json=payload, headers=self._headers(api_key))

    def list(self, client, api_key=DEFAULT_API_KEY, **filters):
        return client.get(BASE_URL, params=filters, headers=self._headers(api_key))

    def get(self, client, id, api_key=DEFAULT_API_KEY):
        return client.get(f"{BASE_URL}{id}", headers=self._headers(api_key))

    def update(self, client, id, payload, api_key=DEFAULT_API_KEY):
        return client.patch(
            f"{BASE_URL}{id}",
            json=payload,
            headers=self._headers(api_key),
        )

    def delete(self, client, id, api_key=DEFAULT_API_KEY):
        return client.delete(f"{BASE_URL}{id}", headers=self._headers(api_key))


class TestCreateTopicRelevanceConfig(BaseTopicRelevanceTest):
    def test_create_success(self, integration_client, clear_database):
        response = self.create(integration_client)

        assert response.status_code == 200
        data = response.json()["data"]

        assert data["name"] == "Maternal Health Scope"
        assert data["prompt_schema_version"] == 1
        assert "Pregnancy care" in data["configuration"]

    def test_create_validation_error_missing_required_fields(
        self, integration_client, clear_database
    ):
        response = integration_client.post(
            BASE_URL,
            json={"name": "missing config"},
            headers=self._headers(),
        )

        assert response.status_code == 422

    def test_create_validation_error_name_too_long(
        self, integration_client, clear_database
    ):
        response = self.create(
            integration_client,
            name="n" * (MAX_TOPIC_RELEVANCE_NAME_LENGTH + 1),
        )

        assert response.status_code == 422


class TestListTopicRelevanceConfigs(BaseTopicRelevanceTest):
    def test_list_success(self, integration_client, clear_database):
        assert self.create(integration_client, name="Scope 1").status_code == 200
        assert self.create(integration_client, name="Scope 2").status_code == 200
        assert self.create(integration_client, name="Scope 3").status_code == 200

        response = self.list(integration_client)

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 3

    def test_list_empty(self, integration_client, clear_database):
        response = self.list(integration_client)

        assert response.status_code == 200
        assert response.json()["data"] == []

    def test_list_pagination_with_limit(self, integration_client, clear_database):
        assert self.create(integration_client, name="Scope 1").status_code == 200
        assert self.create(integration_client, name="Scope 2").status_code == 200
        assert self.create(integration_client, name="Scope 3").status_code == 200

        response = self.list(integration_client, limit=2)

        assert response.status_code == 200
        assert len(response.json()["data"]) == 2

    def test_list_pagination_with_offset_and_limit(
        self, integration_client, clear_database
    ):
        assert self.create(integration_client, name="Scope 1").status_code == 200
        assert self.create(integration_client, name="Scope 2").status_code == 200
        assert self.create(integration_client, name="Scope 3").status_code == 200
        assert self.create(integration_client, name="Scope 4").status_code == 200

        full_response = self.list(integration_client)
        full_data = full_response.json()["data"]

        response = self.list(integration_client, offset=2, limit=2)

        assert response.status_code == 200
        paged_data = response.json()["data"]
        assert len(paged_data) == 2
        assert [item["id"] for item in paged_data] == [
            item["id"] for item in full_data[2:4]
        ]

    def test_list_is_tenant_scoped(self, integration_client, clear_database):
        self.create(integration_client, name="Tenant1 scope")

        response = self.list(integration_client, api_key=ALT_API_KEY)

        assert response.status_code == 200
        assert response.json()["data"] == []


class TestGetTopicRelevanceConfig(BaseTopicRelevanceTest):
    def test_get_success(self, integration_client, clear_database):
        create_resp = self.create(integration_client)
        config_id = create_resp.json()["data"]["id"]

        response = self.get(integration_client, config_id)

        assert response.status_code == 200
        assert response.json()["data"]["id"] == config_id

    def test_get_not_found(self, integration_client, clear_database):
        fake = uuid.uuid4()

        response = self.get(integration_client, fake)
        body = response.json()

        assert response.status_code == 404
        assert body["success"] is False
        assert "Topic relevance preset not found" in body["error"]

    def test_get_other_tenant_not_found(self, integration_client, clear_database):
        create_resp = self.create(integration_client)
        config_id = create_resp.json()["data"]["id"]

        response = self.get(integration_client, config_id, api_key=ALT_API_KEY)
        body = response.json()

        assert response.status_code == 404
        assert body["success"] is False
        assert "Topic relevance preset not found" in body["error"]


class TestUpdateTopicRelevanceConfig(BaseTopicRelevanceTest):
    def test_update_success(self, integration_client, clear_database):
        create_resp = self.create(integration_client)
        config_id = create_resp.json()["data"]["id"]

        response = self.update(
            integration_client,
            config_id,
            {"name": "Updated scope", "prompt_schema_version": 1},
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["name"] == "Updated scope"
        assert data["prompt_schema_version"] == 1

    def test_partial_update(self, integration_client, clear_database):
        create_resp = self.create(integration_client)
        config_id = create_resp.json()["data"]["id"]

        response = self.update(
            integration_client,
            config_id,
            {"is_active": False},
        )

        assert response.status_code == 200
        assert response.json()["data"]["is_active"] is False

    def test_update_not_found(self, integration_client, clear_database):
        fake = uuid.uuid4()

        response = self.update(integration_client, fake, {"name": "x"})
        body = response.json()

        assert response.status_code == 404
        assert body["success"] is False
        assert "Topic relevance preset not found" in body["error"]

    def test_update_other_tenant_not_found(self, integration_client, clear_database):
        create_resp = self.create(integration_client)
        config_id = create_resp.json()["data"]["id"]

        response = self.update(
            integration_client,
            config_id,
            {"name": "updated-by-other-tenant"},
            api_key=ALT_API_KEY,
        )
        body = response.json()

        assert response.status_code == 404
        assert body["success"] is False
        assert "Topic relevance preset not found" in body["error"]


class TestDeleteTopicRelevanceConfig(BaseTopicRelevanceTest):
    def test_delete_success(self, integration_client, clear_database):
        create_resp = self.create(integration_client)
        config_id = create_resp.json()["data"]["id"]

        response = self.delete(integration_client, config_id)

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_delete_not_found(self, integration_client, clear_database):
        fake = uuid.uuid4()

        response = self.delete(integration_client, fake)
        body = response.json()

        assert response.status_code == 404
        assert body["success"] is False
        assert "Topic relevance preset not found" in body["error"]

    def test_delete_other_tenant_not_found(self, integration_client, clear_database):
        create_resp = self.create(integration_client)
        config_id = create_resp.json()["data"]["id"]

        response = self.delete(
            integration_client,
            config_id,
            api_key=ALT_API_KEY,
        )
        body = response.json()

        assert response.status_code == 404
        assert body["success"] is False
        assert "Topic relevance preset not found" in body["error"]
