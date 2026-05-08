import uuid

import pytest

from app.schemas.answer_relevance_prompt import MAX_DESCRIPTION_LENGTH, MAX_NAME_LENGTH

pytestmark = pytest.mark.integration

BASE_URL = "/api/v1/guardrails/answer_relevance_prompts/"
DEFAULT_API_KEY = "org1_project1"
ALT_API_KEY = "org999_project999"

VALID_TEMPLATE = "Query: {query}\nAnswer: {answer}\nIs the answer relevant? YES or NO."
CUSTOM_TEMPLATE = (
    "You are evaluating a health assistant.\n"
    "Query: {query}\n"
    "Answer: {answer}\n"
    "Does the answer address the health query? YES or NO."
)


class BaseAnswerRelevancePromptTest:
    def _headers(self, api_key=DEFAULT_API_KEY):
        return {"X-API-Key": api_key}

    def create(self, client, api_key=DEFAULT_API_KEY, **overrides):
        payload = {
            "name": "Health Relevance",
            "description": "Checks LLM answer relevance for health queries",
            "prompt_template": VALID_TEMPLATE,
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


class TestCreateAnswerRelevancePrompt(BaseAnswerRelevancePromptTest):
    def test_create_success(self, integration_client, clear_database):
        response = self.create(integration_client)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["name"] == "Health Relevance"
        assert "{query}" in data["prompt_template"]
        assert "{answer}" in data["prompt_template"]
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_with_custom_template(self, integration_client, clear_database):
        response = self.create(
            integration_client,
            name="Custom Health Prompt",
            prompt_template=CUSTOM_TEMPLATE,
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert "health assistant" in data["prompt_template"]

    def test_create_validation_error_missing_required_fields(
        self, integration_client, clear_database
    ):
        response = integration_client.post(
            BASE_URL,
            json={"name": "incomplete"},
            headers=self._headers(),
        )

        assert response.status_code == 422

    def test_create_validation_error_template_missing_query_placeholder(
        self, integration_client, clear_database
    ):
        response = self.create(
            integration_client,
            prompt_template="Answer: {answer}\nRelevant? YES or NO.",
        )

        assert response.status_code == 422

    def test_create_validation_error_template_missing_answer_placeholder(
        self, integration_client, clear_database
    ):
        response = self.create(
            integration_client,
            prompt_template="Query: {query}\nRelevant? YES or NO.",
        )

        assert response.status_code == 422

    def test_create_validation_error_template_missing_both_placeholders(
        self, integration_client, clear_database
    ):
        response = self.create(
            integration_client,
            prompt_template="Is this relevant? YES or NO.",
        )

        assert response.status_code == 422

    def test_create_validation_error_name_too_long(
        self, integration_client, clear_database
    ):
        response = self.create(
            integration_client,
            name="n" * (MAX_NAME_LENGTH + 1),
        )

        assert response.status_code == 422

    def test_create_validation_error_description_too_long(
        self, integration_client, clear_database
    ):
        response = self.create(
            integration_client,
            description="d" * (MAX_DESCRIPTION_LENGTH + 1),
        )

        assert response.status_code == 422

    def test_create_validation_error_empty_name(
        self, integration_client, clear_database
    ):
        response = self.create(integration_client, name="")

        assert response.status_code == 422


class TestListAnswerRelevancePrompts(BaseAnswerRelevancePromptTest):
    def test_list_success(self, integration_client, clear_database):
        assert self.create(integration_client, name="Prompt 1").status_code == 200
        assert self.create(integration_client, name="Prompt 2").status_code == 200
        assert self.create(integration_client, name="Prompt 3").status_code == 200

        response = self.list(integration_client)

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 3

    def test_list_empty(self, integration_client, clear_database):
        response = self.list(integration_client)

        assert response.status_code == 200
        assert response.json()["data"] == []

    def test_list_pagination_with_limit(self, integration_client, clear_database):
        for i in range(4):
            self.create(integration_client, name=f"Prompt {i}")

        response = self.list(integration_client, limit=2)

        assert response.status_code == 200
        assert len(response.json()["data"]) == 2

    def test_list_pagination_with_offset_and_limit(
        self, integration_client, clear_database
    ):
        for i in range(4):
            self.create(integration_client, name=f"Prompt {i}")

        full_data = self.list(integration_client).json()["data"]
        response = self.list(integration_client, offset=2, limit=2)

        assert response.status_code == 200
        paged_data = response.json()["data"]
        assert len(paged_data) == 2
        assert [item["id"] for item in paged_data] == [
            item["id"] for item in full_data[2:4]
        ]

    def test_list_is_tenant_scoped(self, integration_client, clear_database):
        self.create(integration_client, name="Tenant1 prompt")

        response = self.list(integration_client, api_key=ALT_API_KEY)

        assert response.status_code == 200
        assert response.json()["data"] == []


class TestGetAnswerRelevancePrompt(BaseAnswerRelevancePromptTest):
    def test_get_success(self, integration_client, clear_database):
        create_resp = self.create(integration_client)
        prompt_id = create_resp.json()["data"]["id"]

        response = self.get(integration_client, prompt_id)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["id"] == prompt_id
        assert "{query}" in data["prompt_template"]
        assert "{answer}" in data["prompt_template"]

    def test_get_not_found(self, integration_client, clear_database):
        response = self.get(integration_client, uuid.uuid4())
        body = response.json()

        assert response.status_code == 404
        assert body["success"] is False
        assert "Answer relevance prompt not found" in body["error"]

    def test_get_other_tenant_not_found(self, integration_client, clear_database):
        create_resp = self.create(integration_client)
        prompt_id = create_resp.json()["data"]["id"]

        response = self.get(integration_client, prompt_id, api_key=ALT_API_KEY)
        body = response.json()

        assert response.status_code == 404
        assert body["success"] is False
        assert "Answer relevance prompt not found" in body["error"]


class TestUpdateAnswerRelevancePrompt(BaseAnswerRelevancePromptTest):
    def test_update_success(self, integration_client, clear_database):
        create_resp = self.create(integration_client)
        prompt_id = create_resp.json()["data"]["id"]

        response = self.update(
            integration_client,
            prompt_id,
            {"name": "Updated Name"},
        )

        assert response.status_code == 200
        assert response.json()["data"]["name"] == "Updated Name"

    def test_update_prompt_template(self, integration_client, clear_database):
        create_resp = self.create(integration_client)
        prompt_id = create_resp.json()["data"]["id"]

        new_template = "Q: {query}\nA: {answer}\nAnswer YES or NO."
        response = self.update(
            integration_client,
            prompt_id,
            {"prompt_template": new_template},
        )

        assert response.status_code == 200
        assert response.json()["data"]["prompt_template"] == new_template

    def test_update_is_active_false(self, integration_client, clear_database):
        create_resp = self.create(integration_client)
        prompt_id = create_resp.json()["data"]["id"]

        response = self.update(integration_client, prompt_id, {"is_active": False})

        assert response.status_code == 200
        assert response.json()["data"]["is_active"] is False

    def test_partial_update_preserves_other_fields(
        self, integration_client, clear_database
    ):
        create_resp = self.create(integration_client)
        original = create_resp.json()["data"]
        prompt_id = original["id"]

        self.update(integration_client, prompt_id, {"name": "New Name"})
        response = self.get(integration_client, prompt_id)
        data = response.json()["data"]

        assert data["name"] == "New Name"
        assert data["prompt_template"] == original["prompt_template"]
        assert data["description"] == original["description"]

    def test_update_validation_error_template_missing_placeholder(
        self, integration_client, clear_database
    ):
        create_resp = self.create(integration_client)
        prompt_id = create_resp.json()["data"]["id"]

        response = self.update(
            integration_client,
            prompt_id,
            {"prompt_template": "No placeholders at all."},
        )

        assert response.status_code == 422

    def test_update_not_found(self, integration_client, clear_database):
        response = self.update(integration_client, uuid.uuid4(), {"name": "x"})
        body = response.json()

        assert response.status_code == 404
        assert body["success"] is False
        assert "Answer relevance prompt not found" in body["error"]

    def test_update_other_tenant_not_found(self, integration_client, clear_database):
        create_resp = self.create(integration_client)
        prompt_id = create_resp.json()["data"]["id"]

        response = self.update(
            integration_client,
            prompt_id,
            {"name": "other-tenant-update"},
            api_key=ALT_API_KEY,
        )
        body = response.json()

        assert response.status_code == 404
        assert body["success"] is False
        assert "Answer relevance prompt not found" in body["error"]


class TestDeleteAnswerRelevancePrompt(BaseAnswerRelevancePromptTest):
    def test_delete_success(self, integration_client, clear_database):
        create_resp = self.create(integration_client)
        prompt_id = create_resp.json()["data"]["id"]

        response = self.delete(integration_client, prompt_id)

        assert response.status_code == 200
        assert response.json()["success"] is True
        assert "deleted" in response.json()["data"]["message"].lower()

    def test_delete_removes_from_list(self, integration_client, clear_database):
        create_resp = self.create(integration_client)
        prompt_id = create_resp.json()["data"]["id"]

        self.delete(integration_client, prompt_id)

        response = self.list(integration_client)
        ids = [item["id"] for item in response.json()["data"]]
        assert prompt_id not in ids

    def test_delete_not_found(self, integration_client, clear_database):
        response = self.delete(integration_client, uuid.uuid4())
        body = response.json()

        assert response.status_code == 404
        assert body["success"] is False
        assert "Answer relevance prompt not found" in body["error"]

    def test_delete_other_tenant_not_found(self, integration_client, clear_database):
        create_resp = self.create(integration_client)
        prompt_id = create_resp.json()["data"]["id"]

        response = self.delete(integration_client, prompt_id, api_key=ALT_API_KEY)
        body = response.json()

        assert response.status_code == 404
        assert body["success"] is False
        assert "Answer relevance prompt not found" in body["error"]
