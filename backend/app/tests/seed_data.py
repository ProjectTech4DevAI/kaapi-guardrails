import json
from pathlib import Path
import uuid
from unittest.mock import MagicMock

from app.core.enum import GuardrailOnFail, Stage, ValidatorType
from app.models.config.validator_config import ValidatorConfig
from app.schemas.ban_list import BanListCreate

SEED_DATA_PATH = Path(__file__).with_name("seed_data.json")


def _load_seed_data() -> dict:
    with SEED_DATA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


DATA = _load_seed_data()

BAN_LIST_UNIT = DATA["ban_list"]["unit"]
BAN_LIST_INTEGRATION = DATA["ban_list"]["integration"]

VALIDATOR_UNIT = DATA["validator"]["unit"]
VALIDATOR_INTEGRATION = DATA["validator"]["integration"]

BAN_LIST_TEST_ID = uuid.UUID(BAN_LIST_UNIT["test_id"])
BAN_LIST_TEST_ORGANIZATION_ID = BAN_LIST_UNIT["organization_id"]
BAN_LIST_TEST_PROJECT_ID = BAN_LIST_UNIT["project_id"]

BAN_LIST_INTEGRATION_ORGANIZATION_ID = BAN_LIST_INTEGRATION["organization_id"]
BAN_LIST_INTEGRATION_PROJECT_ID = BAN_LIST_INTEGRATION["project_id"]
BAN_LIST_PAYLOADS = BAN_LIST_INTEGRATION["payloads"]

VALIDATOR_TEST_ID = uuid.UUID(VALIDATOR_UNIT["validator_id"])
VALIDATOR_TEST_ORGANIZATION_ID = VALIDATOR_UNIT["organization_id"]
VALIDATOR_TEST_PROJECT_ID = VALIDATOR_UNIT["project_id"]
VALIDATOR_TEST_TYPE = ValidatorType[VALIDATOR_UNIT["type"]]
VALIDATOR_TEST_STAGE = Stage[VALIDATOR_UNIT["stage"]]
VALIDATOR_TEST_ON_FAIL = GuardrailOnFail[VALIDATOR_UNIT["on_fail_action"]]
VALIDATOR_TEST_CONFIG = VALIDATOR_UNIT["config"]
VALIDATOR_TEST_IS_ENABLED = VALIDATOR_UNIT["is_enabled"]

VALIDATOR_INTEGRATION_ORGANIZATION_ID = VALIDATOR_INTEGRATION["organization_id"]
VALIDATOR_INTEGRATION_PROJECT_ID = VALIDATOR_INTEGRATION["project_id"]
VALIDATOR_PAYLOADS = VALIDATOR_INTEGRATION["payloads"]


def build_ban_list_create_payload() -> BanListCreate:
    return BanListCreate(**BAN_LIST_UNIT["sample"])


def build_sample_ban_list_mock() -> MagicMock:
    obj = MagicMock()
    obj.id = BAN_LIST_TEST_ID
    obj.name = BAN_LIST_UNIT["sample"]["name"]
    obj.description = BAN_LIST_UNIT["sample"]["description"]
    obj.banned_words = BAN_LIST_UNIT["sample"]["banned_words"]
    obj.organization_id = BAN_LIST_TEST_ORGANIZATION_ID
    obj.project_id = BAN_LIST_TEST_PROJECT_ID
    obj.domain = BAN_LIST_UNIT["sample"]["domain"]
    obj.is_public = BAN_LIST_UNIT["sample"].get("is_public", False)
    return obj


def build_sample_validator_config() -> ValidatorConfig:
    return ValidatorConfig(
        id=VALIDATOR_TEST_ID,
        organization_id=VALIDATOR_TEST_ORGANIZATION_ID,
        project_id=VALIDATOR_TEST_PROJECT_ID,
        type=VALIDATOR_TEST_TYPE,
        stage=VALIDATOR_TEST_STAGE,
        on_fail_action=VALIDATOR_TEST_ON_FAIL,
        is_enabled=VALIDATOR_TEST_IS_ENABLED,
        config=VALIDATOR_TEST_CONFIG,
    )
