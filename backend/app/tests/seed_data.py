import json
from pathlib import Path
import uuid
from unittest.mock import MagicMock

from app.core.enum import GuardrailOnFail, Stage, ValidatorType
from app.models.config.validator_config import ValidatorConfig
from app.schemas.banlist import BanListCreate

SEED_DATA_PATH = Path(__file__).with_name("seed_data.json")


def _load_seed_data() -> dict:
    with SEED_DATA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


DATA = _load_seed_data()

BANLIST_UNIT = DATA["banlist"]["unit"]
BANLIST_INTEGRATION = DATA["banlist"]["integration"]

VALIDATOR_UNIT = DATA["validator"]["unit"]
VALIDATOR_INTEGRATION = DATA["validator"]["integration"]

BANLIST_TEST_ID = uuid.UUID(BANLIST_UNIT["test_id"])
BANLIST_TEST_ORGANIZATION_ID = BANLIST_UNIT["organization_id"]
BANLIST_TEST_PROJECT_ID = BANLIST_UNIT["project_id"]

BANLIST_INTEGRATION_ORGANIZATION_ID = BANLIST_INTEGRATION["organization_id"]
BANLIST_INTEGRATION_PROJECT_ID = BANLIST_INTEGRATION["project_id"]
BAN_LIST_PAYLOADS = BANLIST_INTEGRATION["payloads"]

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


def build_banlist_create_payload() -> BanListCreate:
    return BanListCreate(**BANLIST_UNIT["sample"])


def build_sample_banlist_mock() -> MagicMock:
    obj = MagicMock()
    obj.id = BANLIST_TEST_ID
    obj.name = BANLIST_UNIT["sample"]["name"]
    obj.description = BANLIST_UNIT["sample"]["description"]
    obj.banned_words = BANLIST_UNIT["sample"]["banned_words"]
    obj.organization_id = BANLIST_TEST_ORGANIZATION_ID
    obj.project_id = BANLIST_TEST_PROJECT_ID
    obj.domain = BANLIST_UNIT["sample"]["domain"]
    obj.is_public = BANLIST_UNIT["sample"].get("is_public", False)
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
