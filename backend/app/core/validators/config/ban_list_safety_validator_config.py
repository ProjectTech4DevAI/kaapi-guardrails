from typing import List, Literal, Optional
from uuid import UUID

from guardrails.hub import BanList
from pydantic import model_validator

from app.core.validators.config.base_validator_config import BaseValidatorConfig


class BanListSafetyValidatorConfig(BaseValidatorConfig):
    type: Literal["ban_list"]
    banned_words: Optional[List[str]] = None  # list of banned words to be redacted
    ban_list_id: Optional[UUID] = None

    @model_validator(mode="after")
    def validate_ban_list_source(self):
        if self.banned_words is None and self.ban_list_id is None:
            raise ValueError("Either banned_words or ban_list_id must be provided.")
        return self

    def build(self):
        return BanList(
            banned_words=self.banned_words or [],
            on_fail=self.resolve_on_fail(),
        )
