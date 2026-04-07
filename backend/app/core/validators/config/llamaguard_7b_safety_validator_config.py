from typing import List, Literal, Optional

from guardrails.hub import LlamaGuard7B

from app.core.validators.config.base_validator_config import BaseValidatorConfig

POLICY_NAME_MAP = {
    "no_violence_hate": "O1",
    "no_sexual_content": "O2",
    "no_criminal_planning": "O3",
    "no_guns_and_illegal_weapons": "O4",
    "no_illegal_drugs": "O5",
    "no_encourage_self_harm": "O6",
}


class LlamaGuard7BSafetyValidatorConfig(BaseValidatorConfig):
    type: Literal["llamaguard_7b"]
    policies: Optional[List[str]] = None

    def _resolve_policies(self) -> Optional[List[str]]:
        if self.policies is None:
            return None
        resolved = []
        for policy in self.policies:
            mapped = POLICY_NAME_MAP.get(policy.lower())
            if mapped is None:
                raise ValueError(
                    f"Unknown policy '{policy}'. Valid values: {list(POLICY_NAME_MAP.keys())}"
                )
            resolved.append(mapped)
        return resolved

    def build(self):
        return LlamaGuard7B(
            policies=self._resolve_policies(),
            on_fail=self.resolve_on_fail(),
        )
