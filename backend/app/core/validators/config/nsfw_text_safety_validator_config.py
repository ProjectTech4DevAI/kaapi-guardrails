from typing import Literal, Optional

from guardrails_ai.nsfw_text import NSFWText

from app.core.validators.config.base_validator_config import BaseValidatorConfig


class NSFWTextSafetyValidatorConfig(BaseValidatorConfig):
    type: Literal["nsfw_text"]
    threshold: float = 0.8
    validation_method: str = "sentence"
    device: Optional[str] = "cpu"
    # Must be a model whose text-classification pipeline emits a "NSFW" label,
    # since NSFWText.is_nsfw() only matches label == "NSFW" (see guardrails_ai.nsfw_text) —
    # a toxicity/hate-speech classifier's labels never match, so it would never fail.
    model_name: Optional[str] = "michellejieli/NSFW_text_classifier"

    def build(self):
        return NSFWText(
            threshold=self.threshold,
            validation_method=self.validation_method,
            device=self.device,
            model_name=self.model_name,
            on_fail=self.resolve_on_fail(),
            use_local=True,
        )
