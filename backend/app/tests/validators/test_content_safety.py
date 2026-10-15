from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from guardrails import Guard, OnFailAction
from guardrails.validators import FailResult, PassResult
from pydantic import ValidationError

from app.core.enum import SlurSeverity
from app.core.on_fail_actions import rephrase_query_on_fail
from app.core.validators.config.content_safety_safety_validator_config import (
    ContentSafetySafetyValidatorConfig,
)
from app.core.validators.content_safety import (
    DEFAULT_PROFANITY_THRESHOLD,
    PROFANITY_ERROR_MESSAGE,
    ContentSafety,
)
from app.core.validators.lexical_slur import LexicalSlur

_PREDICT_PROB_PATCH = "app.core.validators.content_safety.predict_prob"
_CONTENT_SAFETY_PATCH = (
    "app.core.validators.config.content_safety_safety_validator_config.ContentSafety"
)


# ---------------------------------------
# Fixtures
# ---------------------------------------
@pytest.fixture
def patch_slur_load(monkeypatch):
    """Use a tiny fixed slur list instead of the curated CSV."""

    def fake_load_slur_list(_self):
        df = pd.DataFrame({"label": ["badword", "highslur"], "severity": ["L", "H"]})
        return df["label"].str.lower().tolist()

    monkeypatch.setattr(LexicalSlur, "load_slur_list", fake_load_slur_list)


@pytest.fixture
def profanity_score():
    """Stub the profanity model so tests don't depend on it. Set
    `.return_value = [score]`; defaults to a clean score."""
    with patch(_PREDICT_PROB_PATCH) as mock:
        mock.return_value = [0.0]
        yield mock


PROFANE = [1.0]


# ---------------------------------------
# ContentSafety validator
# ---------------------------------------
@pytest.mark.usefixtures("patch_slur_load", "profanity_score")
def test_passes_clean_text():
    validator = ContentSafety()

    result = validator.validate("This is a perfectly fine sentence", {})

    assert isinstance(result, PassResult)


@pytest.mark.usefixtures("patch_slur_load", "profanity_score")
def test_slur_only_is_redacted():
    validator = ContentSafety()

    result = validator.validate("You are a BADWORD", {})

    assert isinstance(result, FailResult)
    assert result.error_message == "Mentioned toxic words: badword"
    assert result.fix_value == "you are a [REDACTED_SLUR]"


@pytest.mark.usefixtures("patch_slur_load")
def test_profanity_only_blanks_text(profanity_score):
    validator = ContentSafety()
    profanity_score.return_value = PROFANE

    result = validator.validate("some profane text", {})

    assert isinstance(result, FailResult)
    assert result.error_message == PROFANITY_ERROR_MESSAGE
    assert result.fix_value == ""


@pytest.mark.usefixtures("patch_slur_load")
def test_slur_and_profanity_combines_errors(profanity_score):
    validator = ContentSafety()
    profanity_score.return_value = PROFANE

    result = validator.validate("you badword, some profane text", {})

    assert isinstance(result, FailResult)
    assert result.error_message == (
        f"Mentioned toxic words: badword; {PROFANITY_ERROR_MESSAGE}"
    )
    assert result.fix_value == ""


@pytest.mark.usefixtures("patch_slur_load")
def test_profanity_check_runs_on_redacted_text(profanity_score):
    validator = ContentSafety()

    validator.validate("You are a badword", {})

    checked_texts = profanity_score.call_args.args[0]
    assert checked_texts == ["you are a [REDACTED_SLUR]"]


@pytest.mark.usefixtures("patch_slur_load")
def test_error_message_does_not_echo_input(profanity_score):
    text = "some profane text"
    validator = ContentSafety()
    profanity_score.return_value = PROFANE

    result = validator.validate(text, {})

    assert text not in result.error_message


@pytest.mark.usefixtures("patch_slur_load")
def test_slur_severity_forwarded():
    validator = ContentSafety(slur_severity=SlurSeverity.High)

    assert validator._slur.severity == SlurSeverity.High


@pytest.mark.usefixtures("patch_slur_load")
def test_inner_slur_validator_uses_noop_on_fail():
    validator = ContentSafety()

    assert validator._slur.on_fail_descriptor == OnFailAction.NOOP


@pytest.mark.parametrize(
    ("score", "threshold", "fails"),
    [
        (0.883, DEFAULT_PROFANITY_THRESHOLD, False),  # "kaise ho" with default
        (0.9, DEFAULT_PROFANITY_THRESHOLD, True),  # threshold is inclusive
        (0.95, DEFAULT_PROFANITY_THRESHOLD, True),
        (0.535, 0.5, True),  # ProfanityFree's old cutoff
        (0.95, 0.99, False),
    ],
)
@pytest.mark.usefixtures("patch_slur_load")
def test_profanity_threshold(profanity_score, score, threshold, fails):
    validator = ContentSafety(profanity_threshold=threshold)
    profanity_score.return_value = [score]

    result = validator.validate("some text", {})

    assert isinstance(result, FailResult) is fails


@pytest.mark.usefixtures("patch_slur_load")
def test_rephrase_message_does_not_leak_input(profanity_score):
    """Profanity runs on lowercased/redacted text, so rephrase's str.replace
    can't scrub a message that embeds it; ours must not contain user text."""
    text = "You badword, some profane text"
    validator = ContentSafety()
    profanity_score.return_value = PROFANE

    result = validator.validate(text, {})
    rephrased = rephrase_query_on_fail(text, result)

    assert "badword" in rephrased  # slur name is part of the reason
    assert "some profane text" not in rephrased


@pytest.mark.parametrize(
    ("text", "expected_fix"),
    [
        # Profanity-first would blank all of these (the profanity check has no
        # partial fix); slur-first redacts the slurs and keeps the rest.
        ("you are a bitch", "you are a [REDACTED_SLUR]"),
        (
            "Stop acting like a stupid cunt",
            "stop acting like a [REDACTED_SLUR] [REDACTED_SLUR]",
        ),
        (
            "That guy is a faggot, ignore him",
            "that guy is a [REDACTED_SLUR], ignore him",
        ),
        (
            "What the fuck is this, you bitch",
            "what the [REDACTED_SLUR] is this, you [REDACTED_SLUR]",
        ),
        ("you bhenchod, fuck off", "you [REDACTED_SLUR], [REDACTED_SLUR] off"),
        # Hindi slurs aren't known to the profanity model; only the slur list
        # catches them.
        ("Woh ladki randi hai", "woh ladki [REDACTED_SLUR] hai"),
    ],
)
def test_slur_redacted_before_profanity_with_real_model(text, expected_fix):
    """Runs against the real curated slur list and the real profanity model."""
    validator = ContentSafety()

    result = validator.validate(text, {})

    assert isinstance(result, FailResult)
    assert PROFANITY_ERROR_MESSAGE not in result.error_message
    assert result.fix_value == expected_fix


@pytest.mark.parametrize(
    "text",
    [
        "this is fucking ridiculous",
        "you are such an asshole",
        "piece of shit",
        "go to hell",
        "kill yourself",
    ],
)
def test_english_profanity_still_blanked_with_real_model(text):
    validator = ContentSafety()

    result = validator.validate(text, {})

    assert isinstance(result, FailResult)
    assert result.fix_value == ""


def test_profanity_left_after_redaction_blanks_text_with_real_model():
    """'shit' isn't on the slur list, so the profanity check still fails it."""
    validator = ContentSafety()

    result = validator.validate("You are a randi and a piece of shit", {})

    assert isinstance(result, FailResult)
    assert result.error_message.endswith(PROFANITY_ERROR_MESSAGE)
    assert result.fix_value == ""


@pytest.mark.parametrize(
    "text",
    [
        "Please share the vaccination schedule for my child",
        "mujhe help chahiye",
        "मुझे स्कूल की फीस के बारे में जानकारी चाहिए",
        "I live in Scunthorpe",
        # The English model scores "ho" at 0.883 and "tu" at 0.535; these failed
        # under ProfanityFree's 0.5 cutoff.
        "namaste, kaise ho",
        "aap kaise ho",
        "kya ho raha hai",
        "tu kahan hai",
    ],
)
def test_clean_text_passes_with_real_model(text):
    validator = ContentSafety()

    assert isinstance(validator.validate(text, {}), PassResult)


@pytest.mark.usefixtures("patch_slur_load", "profanity_score")
def test_guard_fix_returns_redacted_text():
    validator = ContentSafety(on_fail=OnFailAction.FIX)

    outcome = Guard().use(validator).validate("You are a badword")

    assert outcome.validated_output == "you are a [REDACTED_SLUR]"


# ---------------------------------------
# ContentSafetySafetyValidatorConfig
# ---------------------------------------
class TestContentSafetySafetyValidatorConfig:
    def test_build_default(self):
        config = ContentSafetySafetyValidatorConfig(type="content_safety")

        with patch(_CONTENT_SAFETY_PATCH) as mock_validator:
            result = config.build()

        assert result == mock_validator.return_value
        _, kwargs = mock_validator.call_args
        assert kwargs["slur_severity"] == SlurSeverity.All
        assert kwargs["profanity_threshold"] == DEFAULT_PROFANITY_THRESHOLD

    def test_slur_severity_forwarded(self):
        config = ContentSafetySafetyValidatorConfig(
            type="content_safety", slur_severity="high"
        )

        with patch(_CONTENT_SAFETY_PATCH) as mock_validator:
            config.build()

        _, kwargs = mock_validator.call_args
        assert kwargs["slur_severity"] == SlurSeverity.High

    def test_only_expected_kwargs_forwarded(self):
        config = ContentSafetySafetyValidatorConfig(type="content_safety")

        with patch(_CONTENT_SAFETY_PATCH) as mock_validator:
            config.build()

        _, kwargs = mock_validator.call_args
        assert set(kwargs.keys()) == {
            "slur_severity",
            "profanity_threshold",
            "on_fail",
        }

    def test_profanity_threshold_forwarded(self):
        config = ContentSafetySafetyValidatorConfig(
            type="content_safety", profanity_threshold=0.75
        )

        with patch(_CONTENT_SAFETY_PATCH) as mock_validator:
            config.build()

        _, kwargs = mock_validator.call_args
        assert kwargs["profanity_threshold"] == 0.75

    @pytest.mark.parametrize("threshold", [-0.1, 1.5])
    def test_out_of_range_profanity_threshold_rejected(self, threshold):
        with pytest.raises(ValidationError):
            ContentSafetySafetyValidatorConfig(
                type="content_safety", profanity_threshold=threshold
            )

    def test_on_fail_fix_resolves_to_callable(self):
        config = ContentSafetySafetyValidatorConfig(
            type="content_safety", on_fail="fix"
        )

        with patch(_CONTENT_SAFETY_PATCH) as mock_validator:
            config.build()

        _, kwargs = mock_validator.call_args
        assert callable(kwargs["on_fail"])

    def test_on_fail_exception_resolves_to_exception_action(self):
        config = ContentSafetySafetyValidatorConfig(
            type="content_safety", on_fail="exception"
        )

        with patch(_CONTENT_SAFETY_PATCH) as mock_validator:
            config.build()

        _, kwargs = mock_validator.call_args
        assert kwargs["on_fail"] == OnFailAction.EXCEPTION

    def test_invalid_slur_severity_rejected(self):
        with pytest.raises(ValidationError):
            ContentSafetySafetyValidatorConfig(
                type="content_safety", slur_severity="extreme"
            )

    def test_languages_not_accepted(self):
        """LexicalSlur ignores `languages`, so the wrapper doesn't expose it."""
        with pytest.raises(ValidationError):
            ContentSafetySafetyValidatorConfig(type="content_safety", languages=["en"])

    def test_wrong_type_literal_rejected(self):
        with pytest.raises(ValidationError):
            ContentSafetySafetyValidatorConfig(type="profanity_free")

    def test_on_fix_sets_reason_when_text_blanked(self):
        config = ContentSafetySafetyValidatorConfig(
            type="content_safety", on_fail="fix"
        )
        fail_result = MagicMock(spec=FailResult)
        fail_result.fix_value = ""

        config._on_fix("some input", fail_result)

        assert config._validator_metadata == {
            "reason": "Empty string has been returned since the validation failed for: content_safety"
        }
