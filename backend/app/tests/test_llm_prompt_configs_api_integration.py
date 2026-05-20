import uuid

import pytest

from app.schemas.llm_prompt_config import MAX_NAME_LENGTH, MAX_DESCRIPTION_LENGTH

pytestmark = pytest.mark.integration

BASE_URL = "/api/v1/guardrails/llm_prompt_configs/"
DEFAULT_API_KEY = "org1_project1"
ALT_API_KEY = "org999_project999"

TOPIC_PROMPT = (
    "Pregnancy care: Questions about prenatal care, supplements, and danger signs. "
    "Postpartum care: Questions about recovery after delivery and breastfeeding."
)
ANSWER_PROMPT = "Query: {query}\nAnswer: {answer}\nIs the answer relevant? YES or NO."
CUSTOM_ANSWER_PROMPT = (
    "You are evaluating a health assistant.\n"
    "Query: {query}\n"
    "Answer: {answer}\n"
    "Does the answer address the health query? YES or NO."
)


class BaseLLMPromptConfigTest:
    def _headers(self, api_key=DEFAULT_API_KEY):
        return {"X-API-Key": api_key}

    def create_topic(self, client, api_key=DEFAULT_API_KEY, **overrides):
        name = overrides.get("name", "Maternal Health Scope")
        payload = {
            "validator_name": "topic_relevance",
            "name": name,
            "description": "Topic guard for maternal health support bot",
            "prompt_schema_version": 1,
            "llm_prompt": f"{TOPIC_PROMPT} Scope name: {name}.",
            **overrides,
        }
        return client.post(BASE_URL, json=payload, headers=self._headers(api_key))

    def create_answer(self, client, api_key=DEFAULT_API_KEY, **overrides):
        payload = {
            "validator_name": "answer_relevance_custom_llm",
            "name": "Health Relevance",
            "description": "Checks LLM answer relevance for health queries",
            "llm_prompt": ANSWER_PROMPT,
            **overrides,
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


class TestCreateLLMPromptConfig(BaseLLMPromptConfigTest):
    def test_create_topic_relevance_success(self, integration_client, clear_database):
        response = self.create_topic(integration_client)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["validator_name"] == "topic_relevance"
        assert data["name"] == "Maternal Health Scope"
        assert "Pregnancy care" in data["llm_prompt"]
        assert data["prompt_schema_version"] == 1
        assert data["is_active"] is True
        assert "id" in data

    def test_create_answer_relevance_success(self, integration_client, clear_database):
        response = self.create_answer(integration_client)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["validator_name"] == "answer_relevance_custom_llm"
        assert "{query}" in data["llm_prompt"]
        assert "{answer}" in data["llm_prompt"]
        assert data["is_active"] is True

    def test_create_answer_relevance_custom_prompt(
        self, integration_client, clear_database
    ):
        response = self.create_answer(
            integration_client,
            name="Custom Health Prompt",
            llm_prompt=CUSTOM_ANSWER_PROMPT,
        )

        assert response.status_code == 200
        assert "health assistant" in response.json()["data"]["llm_prompt"]

    def test_create_validation_error_missing_required_fields(
        self, integration_client, clear_database
    ):
        response = integration_client.post(
            BASE_URL,
            json={"name": "incomplete"},
            headers=self._headers(),
        )
        assert response.status_code == 422

    def test_create_validation_error_invalid_validator_name(
        self, integration_client, clear_database
    ):
        response = integration_client.post(
            BASE_URL,
            json={
                "validator_name": "unknown_validator",
                "name": "test",
                "description": "test",
                "llm_prompt": "test prompt",
            },
            headers=self._headers(),
        )
        assert response.status_code == 422

    def test_create_answer_relevance_missing_query_placeholder(
        self, integration_client, clear_database
    ):
        response = self.create_answer(
            integration_client,
            llm_prompt="Answer: {answer}\nRelevant? YES or NO.",
        )
        assert response.status_code == 422

    def test_create_answer_relevance_missing_answer_placeholder(
        self, integration_client, clear_database
    ):
        response = self.create_answer(
            integration_client,
            llm_prompt="Query: {query}\nRelevant? YES or NO.",
        )
        assert response.status_code == 422

    def test_create_topic_relevance_no_placeholder_validation(
        self, integration_client, clear_database
    ):
        response = self.create_topic(
            integration_client,
            llm_prompt="A plain scope description without any placeholders.",
        )
        assert response.status_code == 200

    def test_create_validation_error_name_too_long(
        self, integration_client, clear_database
    ):
        response = self.create_topic(
            integration_client,
            name="n" * (MAX_NAME_LENGTH + 1),
        )
        assert response.status_code == 422

    def test_create_validation_error_description_too_long(
        self, integration_client, clear_database
    ):
        response = self.create_topic(
            integration_client,
            description="d" * (MAX_DESCRIPTION_LENGTH + 1),
        )
        assert response.status_code == 422


class TestListLLMPromptConfigs(BaseLLMPromptConfigTest):
    def test_list_all_success(self, integration_client, clear_database):
        self.create_topic(integration_client, name="Scope 1")
        self.create_topic(integration_client, name="Scope 2")
        self.create_answer(integration_client, name="Answer Config 1")

        response = self.list(integration_client)

        assert response.status_code == 200
        assert len(response.json()["data"]) == 3

    def test_list_filtered_by_validator_name(self, integration_client, clear_database):
        self.create_topic(integration_client, name="Scope 1")
        self.create_topic(integration_client, name="Scope 2")
        self.create_answer(integration_client, name="Answer Config")

        response = self.list(integration_client, validator_name="topic_relevance")

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 2
        assert all(d["validator_name"] == "topic_relevance" for d in data)

    def test_list_empty(self, integration_client, clear_database):
        response = self.list(integration_client)

        assert response.status_code == 200
        assert response.json()["data"] == []

    def test_list_pagination_with_limit(self, integration_client, clear_database):
        for i in range(4):
            self.create_topic(integration_client, name=f"Scope {i}")

        response = self.list(integration_client, limit=2)

        assert response.status_code == 200
        assert len(response.json()["data"]) == 2

    def test_list_is_tenant_scoped(self, integration_client, clear_database):
        self.create_topic(integration_client, name="Tenant1 scope")

        response = self.list(integration_client, api_key=ALT_API_KEY)

        assert response.status_code == 200
        assert response.json()["data"] == []


class TestGetLLMPromptConfig(BaseLLMPromptConfigTest):
    def test_get_success(self, integration_client, clear_database):
        create_resp = self.create_topic(integration_client)
        config_id = create_resp.json()["data"]["id"]

        response = self.get(integration_client, config_id)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["id"] == config_id
        assert data["validator_name"] == "topic_relevance"

    def test_get_not_found(self, integration_client, clear_database):
        response = self.get(integration_client, uuid.uuid4())
        body = response.json()

        assert response.status_code == 404
        assert body["success"] is False
        assert "LLM prompt config not found" in body["error"]

    def test_get_other_tenant_not_found(self, integration_client, clear_database):
        create_resp = self.create_topic(integration_client)
        config_id = create_resp.json()["data"]["id"]

        response = self.get(integration_client, config_id, api_key=ALT_API_KEY)

        assert response.status_code == 404
        assert response.json()["success"] is False


class TestUpdateLLMPromptConfig(BaseLLMPromptConfigTest):
    def test_update_name_success(self, integration_client, clear_database):
        create_resp = self.create_topic(integration_client)
        config_id = create_resp.json()["data"]["id"]

        response = self.update(integration_client, config_id, {"name": "Updated scope"})

        assert response.status_code == 200
        assert response.json()["data"]["name"] == "Updated scope"

    def test_update_is_active_false(self, integration_client, clear_database):
        create_resp = self.create_topic(integration_client)
        config_id = create_resp.json()["data"]["id"]

        response = self.update(integration_client, config_id, {"is_active": False})

        assert response.status_code == 200
        assert response.json()["data"]["is_active"] is False

    def test_partial_update_preserves_other_fields(
        self, integration_client, clear_database
    ):
        create_resp = self.create_answer(integration_client)
        original = create_resp.json()["data"]
        config_id = original["id"]

        self.update(integration_client, config_id, {"name": "New Name"})
        response = self.get(integration_client, config_id)
        data = response.json()["data"]

        assert data["name"] == "New Name"
        assert data["llm_prompt"] == original["llm_prompt"]
        assert data["description"] == original["description"]

    def test_update_not_found(self, integration_client, clear_database):
        response = self.update(integration_client, uuid.uuid4(), {"name": "x"})

        assert response.status_code == 404
        assert "LLM prompt config not found" in response.json()["error"]

    def test_update_other_tenant_not_found(self, integration_client, clear_database):
        create_resp = self.create_topic(integration_client)
        config_id = create_resp.json()["data"]["id"]

        response = self.update(
            integration_client,
            config_id,
            {"name": "other-tenant-update"},
            api_key=ALT_API_KEY,
        )

        assert response.status_code == 404


class TestDeleteLLMPromptConfig(BaseLLMPromptConfigTest):
    def test_delete_success(self, integration_client, clear_database):
        create_resp = self.create_topic(integration_client)
        config_id = create_resp.json()["data"]["id"]

        response = self.delete(integration_client, config_id)

        assert response.status_code == 200
        assert response.json()["success"] is True
        assert "deleted" in response.json()["data"]["message"].lower()

    def test_delete_removes_from_list(self, integration_client, clear_database):
        create_resp = self.create_topic(integration_client)
        config_id = create_resp.json()["data"]["id"]

        self.delete(integration_client, config_id)

        ids = [item["id"] for item in self.list(integration_client).json()["data"]]
        assert config_id not in ids

    def test_delete_not_found(self, integration_client, clear_database):
        response = self.delete(integration_client, uuid.uuid4())

        assert response.status_code == 404
        assert "LLM prompt config not found" in response.json()["error"]

    def test_delete_other_tenant_not_found(self, integration_client, clear_database):
        create_resp = self.create_topic(integration_client)
        config_id = create_resp.json()["data"]["id"]

        response = self.delete(integration_client, config_id, api_key=ALT_API_KEY)

        assert response.status_code == 404
