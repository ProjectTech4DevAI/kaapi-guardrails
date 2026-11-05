from typing import Any, Dict

from fuzzysearch import find_near_matches
from guardrails.validator_base import (
    ErrorSpan,
    FailResult,
    PassResult,
    ValidationResult,
)
from guardrails_ai.ban_list import BanList as HubBanList


class BanList(HubBanList):
    """Hub BanList with corrected match spans.

    The hub version maps spaceless indices to 1-based positions, so each span
    starts one character late and fix_value keeps the first letter of every
    banned word ("a sonography" -> "a s"). This keeps 0-based positions.
    """

    def validate(self, value: Any, metadata: Dict = {}) -> ValidationResult:
        spaceless_value = value.replace(" ", "").lower()
        # original-string index of each non-space character
        spaceless_index_map = [i for i, ch in enumerate(value) if ch != " "]

        all_matches = []
        for banned_word in self._banned_words:
            spaceless_banned_word = banned_word.replace(" ", "").lower()
            all_matches.extend(
                find_near_matches(
                    spaceless_banned_word, spaceless_value, max_l_dist=self._max_l_dist
                )
            )

        if not all_matches:
            return PassResult()

        error_spans = []
        fix_value = value
        for match in all_matches:
            actual_start = spaceless_index_map[match.start]
            actual_end = spaceless_index_map[match.end - 1] + 1
            triggering_text = value[actual_start:actual_end]
            fix_value = fix_value.replace(triggering_text, "")
            error_spans.append(
                ErrorSpan(
                    start=actual_start,
                    end=actual_end,
                    reason=f"Found match with banned word '{match.matched}' in '{triggering_text}'",
                )
            )
        return FailResult(
            error_message="Output contains banned words",
            error_spans=error_spans,
            fix_value=fix_value,
        )
