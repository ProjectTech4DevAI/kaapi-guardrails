from typing import ClassVar, List, Literal, Optional
from app.models.base_validator_config import BaseValidatorConfig
from app.core.enum import BiasCategories
from app.core.validators.gender_assumption_bias import GenderAssumptionBias

class GenderAssumptionBiasSafetyValidatorConfig(BaseValidatorConfig):
    type: Literal["gender_assumption_bias"]
    categories: Optional[List[BiasCategories]] = [BiasCategories.All]

    def build(self):
        return GenderAssumptionBias(
            categories=self.categories,
            on_fail=self.resolve_on_fail(),
        )
