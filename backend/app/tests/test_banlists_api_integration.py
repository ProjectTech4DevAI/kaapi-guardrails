import uuid
import pytest
from app.schemas.ban_list import (
    MAX_BANNED_WORD_LENGTH,
    MAX_BANNED_WORDS_ITEMS,
    MAX_BAN_LIST_DESCRIPTION_LENGTH,
    MAX_BAN_LIST_NAME_LENGTH,
)
from app.tests.seed_data import BAN_LIST_PAYLOADS

pytestmark = pytest.mark.integration


BASE_URL = "/api/v1/guardrails/ban_lists/"
DEFAULT_API_KEY = "org1_project1"
ALT_API_KEY_999 = "org999_project999"
ALT_API_KEY_2 = "org2_project2"


class BaseBanListTest:
    def _headers(self, api_key=DEFAULT_API_KEY):
        return {"X-API-Key": api_key}

    def create(self, client, payload_key="minimal", api_key=DEFAULT_API_KEY, **kwargs):
        payload = {**BAN_LIST_PAYLOADS[payload_key], **kwargs}
        return client.post(BASE_URL, json=payload, headers=self._headers(api_key))

    def list(self, client, api_key=DEFAULT_API_KEY, **filters):
        return client.get(BASE_URL, params=filters, headers=self._headers(api_key))

    def get(self, client, id, api_key=DEFAULT_API_KEY):
        return client.get(f"{BASE_URL}{id}/", headers=self._headers(api_key))

    def update(self, client, id, payload, api_key=DEFAULT_API_KEY):
        return client.patch(
            f"{BASE_URL}{id}/",
            json=payload,
            headers=self._headers(api_key),
        )

    def delete(self, client, id, api_key=DEFAULT_API_KEY):
        return client.delete(f"{BASE_URL}{id}/", headers=self._headers(api_key))


class TestCreateBanList(BaseBanListTest):
    def test_create_success(self, integration_client, clear_database):
        response = self.create(integration_client, "minimal")

        assert response.status_code == 200
        data = response.json()["data"]

        assert data["name"] == "default"
        assert data["banned_words"] == ["bad"]

    def test_create_validation_error(self, integration_client, clear_database):
        response = integration_client.post(
            BASE_URL,
            json={"name": "missing words"},
            headers=self._headers(),
        )

        assert response.status_code == 422

    def test_create_validation_error_banned_word_too_long(
        self, integration_client, clear_database
    ):
        response = self.create(
            integration_client,
            "minimal",
            banned_words=["a" * (MAX_BANNED_WORD_LENGTH + 1)],
        )

        assert response.status_code == 422

    def test_create_validation_error_too_many_banned_words(
        self, integration_client, clear_database
    ):
        response = self.create(
            integration_client,
            "minimal",
            banned_words=["x"] * (MAX_BANNED_WORDS_ITEMS + 1),
        )

        assert response.status_code == 422

    def test_create_validation_error_name_too_long(
        self, integration_client, clear_database
    ):
        response = self.create(
            integration_client,
            "minimal",
            name="n" * (MAX_BAN_LIST_NAME_LENGTH + 1),
        )

        assert response.status_code == 422

    def test_create_validation_error_description_too_long(
        self, integration_client, clear_database
    ):
        response = self.create(
            integration_client,
            "minimal",
            description="d" * (MAX_BAN_LIST_DESCRIPTION_LENGTH + 1),
        )

        assert response.status_code == 422


class TestListBanLists(BaseBanListTest):
    def test_list_success(self, integration_client, seed_db):
        response = self.list(integration_client)

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 4

    def test_filter_by_domain(self, integration_client, seed_db):
        response = self.list(integration_client, domain="health")

        data = response.json()["data"]

        assert len(data) == 1
        assert data[0]["domain"] == "health"

    def test_list_empty(self, integration_client, clear_database):
        response = self.list(integration_client)

        assert response.json()["data"] == []

    def test_list_pagination_with_limit(self, integration_client, seed_db):
        response = self.list(integration_client, limit=2)

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 2

    def test_list_pagination_with_offset_and_limit(self, integration_client, seed_db):
        full_response = self.list(integration_client)
        full_data = full_response.json()["data"]

        response = self.list(integration_client, offset=2, limit=2)

        assert response.status_code == 200
        paged_data = response.json()["data"]
        assert len(paged_data) == 2
        assert [item["id"] for item in paged_data] == [
            item["id"] for item in full_data[2:4]
        ]


class TestPublicAccess(BaseBanListTest):
    def test_public_visible_to_other_org(self, integration_client, clear_database):
        create_resp = self.create(integration_client, "public")
        ban_id = create_resp.json()["data"]["id"]

        response = self.get(integration_client, ban_id, api_key=ALT_API_KEY_999)

        assert response.status_code == 200


class TestGetBanList(BaseBanListTest):
    def test_get_success(self, integration_client, seed_db):
        list_resp = self.list(integration_client)
        ban_id = list_resp.json()["data"][0]["id"]

        response = self.get(integration_client, ban_id)

        assert response.status_code == 200

    def test_get_not_found(self, integration_client, clear_database):
        fake = uuid.uuid4()
        response = self.get(integration_client, fake)
        body = response.json()

        assert response.status_code == 404
        assert body["success"] is False
        assert body["metadata"] is None
        assert "Ban list not found" in body["error"]

    def test_get_wrong_owner_private(self, integration_client, seed_db):
        list_resp = self.list(integration_client)
        private_ban_list = next(
            item for item in list_resp.json()["data"] if not item["is_public"]
        )
        ban_id = private_ban_list["id"]

        response = self.get(integration_client, ban_id, api_key=ALT_API_KEY_2)
        body = response.json()

        assert response.status_code == 403
        assert body["success"] is False
        assert "permission" in body["error"].lower()


class TestUpdateBanList(BaseBanListTest):
    def test_update_success(self, integration_client, seed_db):
        list_resp = self.list(integration_client)
        ban_id = list_resp.json()["data"][0]["id"]

        response = self.update(
            integration_client,
            ban_id,
            {"banned_words": ["bad", "worse"]},
        )

        assert response.status_code == 200

        data = response.json()["data"]
        assert data["banned_words"] == ["bad", "worse"]

    def test_partial_update(self, integration_client, seed_db):
        list_resp = self.list(integration_client)
        ban_id = list_resp.json()["data"][0]["id"]

        response = self.update(integration_client, ban_id, {"name": "updated"})

        assert response.json()["data"]["name"] == "updated"

    def test_update_not_found(self, integration_client, clear_database):
        fake = uuid.uuid4()

        response = self.update(integration_client, fake, {"name": "x"})
        body = response.json()

        assert response.status_code == 404
        assert body["success"] is False
        assert "Ban list not found" in body["error"]

    def test_update_public_wrong_owner_fails(self, integration_client, clear_database):
        create_resp = self.create(integration_client, "public")
        ban_id = create_resp.json()["data"]["id"]

        response = self.update(
            integration_client,
            ban_id,
            {"name": "updated-by-other-org"},
            api_key=ALT_API_KEY_999,
        )
        body = response.json()

        assert response.status_code == 403
        assert body["success"] is False
        assert "permission" in body["error"].lower()


class TestDeleteBanList(BaseBanListTest):
    def test_delete_success(self, integration_client, seed_db):
        list_resp = self.list(integration_client)
        ban_id = list_resp.json()["data"][0]["id"]

        response = self.delete(integration_client, ban_id)

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_delete_not_found(self, integration_client, clear_database):
        fake = uuid.uuid4()

        response = self.delete(integration_client, fake)
        body = response.json()

        assert response.status_code == 404
        assert body["success"] is False
        assert "Ban list not found" in body["error"]

    def test_delete_wrong_owner(self, integration_client, seed_db):
        list_resp = self.list(integration_client)
        private_ban_list = next(
            item for item in list_resp.json()["data"] if not item["is_public"]
        )
        ban_id = private_ban_list["id"]

        response = self.delete(
            integration_client,
            ban_id,
            api_key=ALT_API_KEY_999,
        )
        body = response.json()

        assert response.status_code == 403
        assert body["success"] is False
        assert "permission" in body["error"].lower()

    def test_delete_public_wrong_owner_fails(self, integration_client, clear_database):
        create_resp = self.create(integration_client, "public")
        ban_id = create_resp.json()["data"]["id"]

        response = self.delete(
            integration_client,
            ban_id,
            api_key=ALT_API_KEY_999,
        )
        body = response.json()

        assert response.status_code == 403
        assert body["success"] is False
        assert "permission" in body["error"].lower()
