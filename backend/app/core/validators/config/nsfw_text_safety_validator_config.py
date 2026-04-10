from typing import Literal, Optional

from guardrails.hub import NSFWText

from app.core.validators.config.base_validator_config import BaseValidatorConfig


class NSFWTextSafetyValidatorConfig(BaseValidatorConfig):
    type: Literal["nsfw_text"]
    threshold: float = 0.8
    validation_method: str = "sentence"
    device: Optional[str] = "cpu"
    model_name: Optional[str] = "textdetox/xlmr-large-toxicity-classifier"

    def build(self):
        return NSFWText(
            threshold=self.threshold,
            validation_method=self.validation_method,
            device=self.device,
            model_name=self.model_name,
            on_fail=self.resolve_on_fail(),
        )
