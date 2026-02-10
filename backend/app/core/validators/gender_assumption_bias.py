import re
from typing import Callable, List, Optional

import pandas
from guardrails import OnFailAction
from guardrails.validators import (
    FailResult,
    PassResult,
    register_validator,
    ValidationResult,
    Validator,
)

from app.core.config import Settings
from app.core.enum import BiasCategories


@register_validator(name="gender-assumption-bias", data_type="string")
class GenderAssumptionBias(Validator):
    """
    Validate text for the presence of gender assumption in LLM generated outputs.
    """

    def __init__(
        self,
        categories: Optional[List[BiasCategories]] = None,
        on_fail: Optional[Callable] = OnFailAction.FIX,
    ):
        self.categories = categories or [BiasCategories.All]
        self.gender_bias_list = self.load_gender_bias_list(self.categories)
        super().__init__(on_fail=on_fail)

    def _validate(self, value: str, metadata: dict = None) -> ValidationResult:
        detected_biased_words = []
        bias_check = False

        for entry in self.gender_bias_list:
            word = entry["word"]
            neutral_term = entry["neutral-term"]

            pattern = rf"\b{re.escape(word)}\b"

            if re.search(pattern, value, flags=re.IGNORECASE):
                detected_biased_words.append(word)

                value = re.sub(pattern, neutral_term, value, flags=re.IGNORECASE)
                bias_check = True

        if bias_check:
            return FailResult(
                error_message=f"Detected gender assumption bias: {detected_biased_words}",
                fix_value=value,
            )

        return PassResult(value=value)

    def load_gender_bias_list(self, categories):
        file_path = Settings.GENDER_BIAS_LIST_FILEPATH
        neutral_term_col = "neutral-term"
        gender_bias_list = []

        try:
            df = pandas.read_csv(file_path)
        except FileNotFoundError:
            raise FileNotFoundError(f"Gender bias file not found at {file_path}")
        except Exception as e:
            raise ValueError(f"Failed to load gender bias list from {file_path}: {e}")

        df["word"] = df["word"].str.lower()
        df[neutral_term_col] = df[neutral_term_col].str.lower()

        for category in categories:
            if category == BiasCategories.All:
                temp = df
            else:
                temp = df[df["type"] == category.value]

            rows = temp.to_dict(orient="records")
            for row in rows:
                gender_bias_list.append(
                    {"word": row["word"], neutral_term_col: row[neutral_term_col]}
                )
        return gender_bias_list
