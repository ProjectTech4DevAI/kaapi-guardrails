from typing import List, Literal, Optional

from guardrails.hub import LlamaGuard7B

from app.core.validators.config.base_validator_config import BaseValidatorConfig


class LlamaGuard7BSafetyValidatorConfig(BaseValidatorConfig):
    type: Literal["llamaguard_7b"]
    policies: Optional[List[str]] = None

    def build(self):
        return LlamaGuard7B(
            policies=self.policies,
            on_fail=self.resolve_on_fail(),
        )
