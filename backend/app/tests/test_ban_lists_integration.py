import uuid
import pytest
from sqlmodel import Session, delete

from app.core.db import engine
from app.models.config.ban_list_table import BanList

pytestmark = pytest.mark.integration


# Test data constants
TEST_ORG_ID = 1
TEST_PROJECT_ID = 1
BASE_URL = "/api/v1/guardrails/ban-lists/"
DEFAULT_QUERY = f"?org_id={TEST_ORG_ID}&project_id={TEST_PROJECT_ID}"


BAN_LIST_PAYLOADS = {
    "minimal": {
        "name": "default",
        "description": "basic list",
        "banned_words": ["bad"],
        "domain": "general",
    },
    "health": {
        "name": "health-list",
        "description": "healthcare words",
        "banned_words": ["gender detection", "sonography"],
        "domain": "health",
    },
    "edu": {
        "name": "edu-list",
        "description": "education words",
        "banned_words": ["cheating"],
        "domain": "edu",
    },
    "public": {
        "name": "public-list",
        "description": "shared",
        "banned_words": ["shared"],
        "is_public": True,
        "domain": "general",
    },
}


@pytest.fixture
def clear_database():
    with Session(engine) as session:
        session.exec(delete(BanList))
        session.commit()

    yield

    with Session(engine) as session:
        session.exec(delete(BanList))
        session.commit()


class BaseBanListTest:

    def create(self, client, payload_key="minimal", **kwargs):
        payload = {**BAN_LIST_PAYLOADS[payload_key], **kwargs}
        return client.post(f"{BASE_URL}{DEFAULT_QUERY}", json=payload)

    def list(self, client, **filters):
        params = DEFAULT_QUERY
        if filters:
            params += "&" + "&".join(f"{k}={v}" for k, v in filters.items())
        return client.get(f"{BASE_URL}{params}")

    def get(self, client, id, org=TEST_ORG_ID, project=TEST_PROJECT_ID):
        return client.get(f"{BASE_URL}{id}/?org_id={org}&project_id={project}")

    def update(self, client, id, payload):
        return client.patch(f"{BASE_URL}{id}/{DEFAULT_QUERY}", json=payload)

    def delete(self, client, id):
        return client.delete(f"{BASE_URL}{id}/{DEFAULT_QUERY}")


class TestCreateBanList(BaseBanListTest):

    def test_create_success(self, integration_client, clear_database):
        response = self.create(integration_client, "minimal")

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "default"
        assert data["banned_words"] == ["bad"]
        assert "id" in data

    def test_create_validation_error(self, integration_client, clear_database):
        response = integration_client.post(
            f"{BASE_URL}{DEFAULT_QUERY}",
            json={"name": "missing words"},
        )

        assert response.status_code == 422


class TestListBanLists(BaseBanListTest):

    def test_list_success(self, integration_client, clear_database):
        self.create(integration_client, "minimal")
        self.create(integration_client, "health")

        response = self.list(integration_client)

        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_filter_by_domain(self, integration_client, clear_database):
        self.create(integration_client, "health")
        self.create(integration_client, "edu")

        response = self.list(integration_client, domain="health")

        data = response.json()
        assert len(data) == 1
        assert data[0]["domain"] == "health"

    def test_list_empty(self, integration_client, clear_database):
        response = self.list(integration_client)
        assert response.json() == []


class TestPublicAccess(BaseBanListTest):

    def test_public_visible_to_other_org(self, integration_client, clear_database):
        create_resp = self.create(integration_client, "public")
        ban_id = create_resp.json()["id"]

        response = self.get(integration_client, ban_id, org=999, project=999)

        # public lists should still be readable
        assert response.status_code == 200


class TestGetBanList(BaseBanListTest):

    def test_get_success(self, integration_client, clear_database):
        create_resp = self.create(integration_client, "minimal")
        ban_id = create_resp.json()["id"]

        response = self.get(integration_client, ban_id)

        assert response.status_code == 200

    def test_get_not_found(self, integration_client, clear_database):
        fake = uuid.uuid4()
        response = self.get(integration_client, fake)

        assert response.status_code == 404

    def test_get_wrong_owner_private(self, integration_client, clear_database):
        create_resp = self.create(integration_client, "minimal")
        ban_id = create_resp.json()["id"]

        response = self.get(integration_client, ban_id, org=2, project=2)

        assert response.status_code in (403, 404)


class TestUpdateBanList(BaseBanListTest):

    def test_update_success(self, integration_client, clear_database):
        create_resp = self.create(integration_client, "minimal")
        ban_id = create_resp.json()["id"]

        response = self.update(
            integration_client,
            ban_id,
            {"banned_words": ["bad", "worse"]},
        )

        assert response.status_code == 200
        assert response.json()["banned_words"] == ["bad", "worse"]

    def test_partial_update(self, integration_client, clear_database):
        create_resp = self.create(integration_client, "minimal")
        ban_id = create_resp.json()["id"]

        response = self.update(integration_client, ban_id, {"name": "updated"})

        assert response.json()["name"] == "updated"

    def test_update_not_found(self, integration_client, clear_database):
        fake = uuid.uuid4()

        response = self.update(integration_client, fake, {"name": "x"})
        assert response.status_code == 404


class TestDeleteBanList(BaseBanListTest):

    def test_delete_success(self, integration_client, clear_database):
        create_resp = self.create(integration_client, "minimal")
        ban_id = create_resp.json()["id"]

        response = self.delete(integration_client, ban_id)

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_delete_not_found(self, integration_client, clear_database):
        fake = uuid.uuid4()

        response = self.delete(integration_client, fake)
        assert response.status_code == 404

    def test_delete_wrong_owner(self, integration_client, clear_database):
        create_resp = self.create(integration_client, "minimal")
        ban_id = create_resp.json()["id"]

        response = integration_client.delete(
            f"{BASE_URL}{ban_id}/?org_id=999&project_id=999"
        )

        assert response.status_code in (403, 404)
