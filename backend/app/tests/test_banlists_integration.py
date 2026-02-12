import uuid
import pytest
from app.tests.seed_data import (
    BANLIST_INTEGRATION_ORGANIZATION_ID,
    BANLIST_INTEGRATION_PROJECT_ID,
    BAN_LIST_PAYLOADS,
)

pytestmark = pytest.mark.integration


BASE_URL = "/api/v1/guardrails/ban-lists/"
DEFAULT_QUERY = (
    f"?organization_id={BANLIST_INTEGRATION_ORGANIZATION_ID}"
    f"&project_id={BANLIST_INTEGRATION_PROJECT_ID}"
)


class BaseBanListTest:
    def create(self, client, payload_key="minimal", **kwargs):
        payload = {**BAN_LIST_PAYLOADS[payload_key], **kwargs}
        return client.post(f"{BASE_URL}{DEFAULT_QUERY}", json=payload)

    def list(self, client, **filters):
        params = DEFAULT_QUERY
        if filters:
            params += "&" + "&".join(f"{k}={v}" for k, v in filters.items())
        return client.get(f"{BASE_URL}{params}")

    def get(
        self,
        client,
        id,
        org=BANLIST_INTEGRATION_ORGANIZATION_ID,
        project=BANLIST_INTEGRATION_PROJECT_ID,
    ):
        return client.get(f"{BASE_URL}{id}/?organization_id={org}&project_id={project}")

    def update(self, client, id, payload):
        return client.patch(f"{BASE_URL}{id}/{DEFAULT_QUERY}", json=payload)

    def delete(self, client, id):
        return client.delete(f"{BASE_URL}{id}/{DEFAULT_QUERY}")


class TestCreateBanList(BaseBanListTest):
    def test_create_success(self, integration_client, clear_database):
        response = self.create(integration_client, "minimal")

        assert response.status_code == 200
        data = response.json()["data"]

        assert data["name"] == "default"
        assert data["banned_words"] == ["bad"]

    def test_create_validation_error(self, integration_client, clear_database):
        response = integration_client.post(
            f"{BASE_URL}{DEFAULT_QUERY}",
            json={"name": "missing words"},
        )

        assert response.status_code == 422


class TestListBanLists(BaseBanListTest):
    def test_list_success(self, integration_client, clear_database, seed_db):
        response = self.list(integration_client)

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 4

    def test_filter_by_domain(self, integration_client, clear_database, seed_db):
        response = self.list(integration_client, domain="health")

        data = response.json()["data"]

        assert len(data) == 1
        assert data[0]["domain"] == "health"

    def test_list_empty(self, integration_client, clear_database):
        response = self.list(integration_client)

        assert response.json()["data"] == []


class TestPublicAccess(BaseBanListTest):
    def test_public_visible_to_other_org(self, integration_client, clear_database):
        create_resp = self.create(integration_client, "public")
        ban_id = create_resp.json()["data"]["id"]

        response = self.get(integration_client, ban_id, org=999, project=999)

        assert response.status_code == 200


class TestGetBanList(BaseBanListTest):
    def test_get_success(self, integration_client, clear_database, seed_db):
        list_resp = self.list(integration_client)
        ban_id = list_resp.json()["data"][0]["id"]

        response = self.get(integration_client, ban_id)

        assert response.status_code == 200

    def test_get_not_found(self, integration_client, clear_database):
        fake = uuid.uuid4()
        response = self.get(integration_client, fake)
        body = response.json()

        assert response.status_code == 200
        assert body["success"] is False
        assert "Banlist not found" in body["error"]

    def test_get_wrong_owner_private(self, integration_client, clear_database, seed_db):
        list_resp = self.list(integration_client)
        private_banlist = next(
            item for item in list_resp.json()["data"] if not item["is_public"]
        )
        ban_id = private_banlist["id"]

        response = self.get(integration_client, ban_id, org=2, project=2)
        body = response.json()

        assert response.status_code == 200
        assert body["success"] is False
        assert "permission" in body["error"].lower()


class TestUpdateBanList(BaseBanListTest):
    def test_update_success(self, integration_client, clear_database, seed_db):
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

    def test_partial_update(self, integration_client, clear_database, seed_db):
        list_resp = self.list(integration_client)
        ban_id = list_resp.json()["data"][0]["id"]

        response = self.update(integration_client, ban_id, {"name": "updated"})

        assert response.json()["data"]["name"] == "updated"

    def test_update_not_found(self, integration_client, clear_database):
        fake = uuid.uuid4()

        response = self.update(integration_client, fake, {"name": "x"})
        body = response.json()

        assert response.status_code == 200
        assert body["success"] is False
        assert "Banlist not found" in body["error"]


class TestDeleteBanList(BaseBanListTest):
    def test_delete_success(self, integration_client, clear_database, seed_db):
        list_resp = self.list(integration_client)
        ban_id = list_resp.json()["data"][0]["id"]

        response = self.delete(integration_client, ban_id)

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_delete_not_found(self, integration_client, clear_database):
        fake = uuid.uuid4()

        response = self.delete(integration_client, fake)
        body = response.json()

        assert response.status_code == 200
        assert body["success"] is False
        assert "Banlist not found" in body["error"]

    def test_delete_wrong_owner(self, integration_client, clear_database, seed_db):
        list_resp = self.list(integration_client)
        private_banlist = next(
            item for item in list_resp.json()["data"] if not item["is_public"]
        )
        ban_id = private_banlist["id"]

        response = integration_client.delete(
            f"{BASE_URL}{ban_id}/?organization_id=999&project_id=999"
        )
        body = response.json()

        assert response.status_code == 200
        assert body["success"] is False
        assert "permission" in body["error"].lower()
