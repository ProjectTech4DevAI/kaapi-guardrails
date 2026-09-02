from typing import List, Literal, Optional

from app.core.validators.config.base_validator_config import BaseValidatorConfig

# guardrails.hub is unavailable: the Guardrails Hub CLI/registry and its hosted
# inference servers were shut down 2026-08-25. The PyPI replacement
# (guardrails-ai-llamaguard-7b) only supports remote inference via a
# self-hosted validation_endpoint, which we don't have yet. Import is deferred
# to build() so this module (and the schema/registry that imports it) stays
# loadable; only actually building this validator fails until that's resolved.

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
        from guardrails.hub import LlamaGuard7B

        return LlamaGuard7B(
            policies=self._resolve_policies(),
            on_fail=self.resolve_on_fail(),  # type: ignore[arg-type]
        )
