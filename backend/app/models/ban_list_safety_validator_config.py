from guardrails.hub import BanList
from guardrails.utils.validator_utils import get_validator
from typing import ClassVar, List, Literal

from app.models.base_validator_config import BaseValidatorConfig
from app.core.constants import BAN_LIST

class BanListSafetyValidatorConfig(BaseValidatorConfig):
    type: Literal[f"{BAN_LIST}"]
    banned_words: List[str]

    def build(self):
        return BanList(
            banned_words=self.banned_words,
            on_fail=self.resolve_on_fail(),
        )