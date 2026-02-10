import re
import string
import unicodedata
from typing import Callable, Optional

import emoji
import ftfy
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
from app.core.enum import SlurSeverity


@register_validator(name="lexical-slur", data_type="string")
class LexicalSlur(Validator):
    """
    Validate text for the presence of lexical slurs using a predefined list.
    """

    _SLUR_CACHE: dict = {}

    def __init__(
        self,
        severity: SlurSeverity = SlurSeverity.All,
        languages: Optional[list] = None,
        on_fail: Optional[Callable] = OnFailAction.FIX,
    ):
        self.severity = severity
        self.languages = languages or ["en", "hi"]
        self.slur_list = self.load_slur_list()
        self._compile_slur_patterns()
        super().__init__(on_fail=on_fail, search_words=self.slur_list)

    def _validate(self, value: str, metadata: dict = None) -> ValidationResult:
        original_text = value
        normalized_text = self.normalize_for_matching(value)
        detected_slurs = []

        for slur, pattern in self._slur_patterns:
            if pattern.search(normalized_text):
                detected_slurs.append(slur)

        if not detected_slurs:
            return PassResult(value=original_text)

        redacted_text = normalized_text
        for slur, pattern in self._slur_patterns:
            if slur in detected_slurs:
                redacted_text = pattern.sub("[REDACTED_SLUR]", redacted_text)

        return FailResult(
            error_message=f"Mentioned toxic words: {', '.join(detected_slurs)}",
            fix_value=redacted_text,
        )

    def normalize_for_matching(self, text: str) -> str:
        """
        Normalize input text for detection:
        - remove emojis
        - fix encoding issues
        - normalize unicode (NFKC)
        - lowercase
        - normalize whitespace
        """
        text = self.remove_emojis(text)
        text = ftfy.fix_text(text)
        text = unicodedata.normalize("NFKC", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text.lower()

    def remove_emojis(self, text):
        """
        Removed emojis from given string.
        """
        return emoji.replace_emoji(text, replace="")

    def _compile_slur_patterns(self):
        """
        Compile regex patterns for all slurs.
        Uses Unicode-safe boundaries and longest-match-first ordering.
        """
        self._slur_patterns = []

        for slur in self.slur_list:
            escaped = re.escape(slur)
            pattern = rf"(?<!\w){escaped}(?!\w)"
            compiled = re.compile(pattern, re.IGNORECASE)
            self._slur_patterns.append((slur, compiled))

        self._slur_patterns.sort(key=lambda x: len(x[0]), reverse=True)

    def load_slur_list(self):
        cache_key = (
            self.severity.value
            if hasattr(self.severity, "value")
            else str(self.severity)
        )

        if cache_key in self._SLUR_CACHE:
            return self._SLUR_CACHE[cache_key]

        file_path = Settings.SLUR_LIST_FILEPATH

        try:
            df = pandas.read_csv(file_path)
        except FileNotFoundError:
            raise FileNotFoundError(f"Slur list file not found at {file_path}")
        except Exception as e:
            raise ValueError(f"Failed to load slur list from {file_path}: {e}")

        required_columns = ["label", "severity"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(
                f"Slur list CSV missing required columns: {missing_columns}"
            )

        df["label"] = df["label"].str.lower()

        if self.severity == SlurSeverity.Low:
            slurs = df[df["severity"].isin(["L", "M", "H"])]["label"].tolist()
        elif self.severity == SlurSeverity.Medium:
            slurs = df[df["severity"].isin(["M", "H"])]["label"].tolist()
        elif self.severity == SlurSeverity.High:
            slurs = df[df["severity"] == "H"]["label"].tolist()
        else:
            slurs = df["label"].tolist()

        self._SLUR_CACHE[cache_key] = slurs
        return slurs
