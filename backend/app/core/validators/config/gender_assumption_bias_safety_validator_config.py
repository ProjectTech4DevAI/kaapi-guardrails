from typing import List, Literal, Optional

from app.core.enum import BiasCategories
from app.core.validators.gender_assumption_bias import GenderAssumptionBias
from app.core.validators.config.base_validator_config import BaseValidatorConfig


class GenderAssumptionBiasSafetyValidatorConfig(BaseValidatorConfig):
    type: Literal["gender_assumption_bias"]
    categories: Optional[List[BiasCategories]] = [
        BiasCategories.All
    ]  # preferred category (based on sector)

    def build(self):
        return GenderAssumptionBias(
            categories=self.categories,
            on_fail=self.resolve_on_fail(),
        )
