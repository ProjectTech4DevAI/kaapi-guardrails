from typing import Literal

from guardrails.hub import ProfanityFree

from app.core.validators.config.base_validator_config import BaseValidatorConfig


class ProfanityFreeSafetyValidatorConfig(BaseValidatorConfig):
    type: Literal["profanity_free"]

    def build(self):
        return ProfanityFree(
            on_fail=self.resolve_on_fail(),
        )
