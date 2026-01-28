from typing import List, Literal

from guardrails.hub import BanList

from app.models.base_validator_config import BaseValidatorConfig

class BanListSafetyValidatorConfig(BaseValidatorConfig):
    type: Literal["ban_list"]
    banned_words: List[str] #list of banned words to be redacted

    def build(self):
        return BanList(
            banned_words=self.banned_words,
            on_fail=self.resolve_on_fail(),
        )