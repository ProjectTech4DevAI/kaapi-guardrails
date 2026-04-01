from typing import Literal, Optional

from guardrails.hub import ToxicLanguage

from app.core.validators.config.base_validator_config import BaseValidatorConfig


class ToxicLanguageSafetyValidatorConfig(BaseValidatorConfig):
    type: Literal["toxic_language"]
    threshold: float = 0.5
    validation_method: str = "sentence"
    device: Optional[str] = "cpu"
    model_name: Optional[str] = "unbiased-small"

    def build(self):
        return ToxicLanguage(
            threshold=self.threshold,
            validation_method=self.validation_method,
            device=self.device,
            model_name=self.model_name,
            on_fail=self.resolve_on_fail(),
        )
