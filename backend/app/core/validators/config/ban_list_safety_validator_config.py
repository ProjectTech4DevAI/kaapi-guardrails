from typing import List, Literal, Optional
from uuid import UUID

from guardrails.hub import BanList

from app.core.validators.config.base_validator_config import BaseValidatorConfig


class BanListSafetyValidatorConfig(BaseValidatorConfig):
    type: Literal["ban_list"]
    banned_words: Optional[List[str]] = None  # list of banned words to be redacted
    ban_list_id: UUID

    def build(self):
        return BanList(
            banned_words=self.banned_words,
            on_fail=self.resolve_on_fail(),
        )
