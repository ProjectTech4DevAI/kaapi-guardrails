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

# Devanagari vowel signs, virama and nukta are not \w in Python's re, so \b
# splits words at them ("छात्र" would match inside "छात्रा"). Treat them as
# word characters when checking boundaries.
WORD_CHARS = r"\w\u0900-\u0903\u093a-\u094f\u0951-\u0957\u0962\u0963"

# "her" is either an object ("help her" -> "them") or a possessive ("her
# patient" -> "their"). It is treated as an object when followed by the end of
# the text, punctuation, or one of these words; otherwise as a possessive.
OBJECT_HER_FOLLOWERS = {
    "a", "an", "the", "this", "that", "these", "those", "some", "any", "every",
    "to", "for", "with", "about", "at", "in", "on", "from", "by", "of", "into",
    "up", "out", "down", "off", "back", "over", "after", "before", "and", "or",
    "but", "so", "if", "when", "because", "as", "than", "now", "again", "today",
    "tomorrow", "yesterday", "soon", "later", "too", "also", "please", "first",
    "well", "very", "more", "just", "not", "already", "yet", "here", "there",
    "home", "it", "me", "you", "him", "them", "us", "everything", "something",
    "anything", "nothing", "is", "was", "will", "can", "should",
}


def match_case(source: str, replacement: str) -> str:
    """Carry the matched word's casing over to its replacement."""
    if len(source) > 1 and source.isupper():
        return replacement.upper()
    if source[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def neutral_her(value: str, end: int) -> str:
    next_word = re.match(r"\s+([A-Za-z']+)", value[end:])
    if next_word and next_word.group(1).lower() not in OBJECT_HER_FOLLOWERS:
        return "their"
    return "them"


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

    def _validate(self, value: str, metadata: dict | None = None) -> ValidationResult:
        detected_biased_words = []
        bias_check = False

        for entry in self.gender_bias_list:
            word = entry["word"]
            neutral_term = entry["neutral-term"]

            pattern = rf"(?<![{WORD_CHARS}]){re.escape(word)}(?![{WORD_CHARS}])"

            if re.search(pattern, value, flags=re.IGNORECASE):
                detected_biased_words.append(word)

                def replace(match, current=value, neutral_term=neutral_term):
                    term = (
                        neutral_her(current, match.end())
                        if match.group(0).lower() == "her"
                        else neutral_term
                    )
                    return match_case(match.group(0), term)

                value = re.sub(pattern, replace, value, flags=re.IGNORECASE)
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
                # Rows that map a word to itself (e.g. "woh") change nothing,
                # so they would only flag already-neutral text.
                if row["word"] == row[neutral_term_col]:
                    continue
                gender_bias_list.append(
                    {"word": row["word"], neutral_term_col: row[neutral_term_col]}
                )
        return gender_bias_list
