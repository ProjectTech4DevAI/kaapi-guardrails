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
    PROFANITY_ERROR_MESSAGE,
    ContentSafety,
)
from app.core.validators.lexical_slur import LexicalSlur

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


def _set_profanity(validator: ContentSafety, profane: bool) -> MagicMock:
    """Stub the inner ProfanityFree so tests don't depend on the ML model."""
    result = (
        FailResult(error_message="anything contains profanity.", fix_value="")
        if profane
        else PassResult()
    )
    mock = MagicMock(return_value=result)
    validator._profanity.validate = mock
    return mock


# ---------------------------------------
# ContentSafety validator
# ---------------------------------------
@pytest.mark.usefixtures("patch_slur_load")
def test_passes_clean_text():
    validator = ContentSafety()
    _set_profanity(validator, profane=False)

    result = validator.validate("This is a perfectly fine sentence", {})

    assert isinstance(result, PassResult)


@pytest.mark.usefixtures("patch_slur_load")
def test_slur_only_is_redacted():
    validator = ContentSafety()
    _set_profanity(validator, profane=False)

    result = validator.validate("You are a BADWORD", {})

    assert isinstance(result, FailResult)
    assert result.error_message == "Mentioned toxic words: badword"
    assert result.fix_value == "you are a [REDACTED_SLUR]"


@pytest.mark.usefixtures("patch_slur_load")
def test_profanity_only_blanks_text():
    validator = ContentSafety()
    _set_profanity(validator, profane=True)

    result = validator.validate("some profane text", {})

    assert isinstance(result, FailResult)
    assert result.error_message == PROFANITY_ERROR_MESSAGE
    assert result.fix_value == ""


@pytest.mark.usefixtures("patch_slur_load")
def test_slur_and_profanity_combines_errors():
    validator = ContentSafety()
    _set_profanity(validator, profane=True)

    result = validator.validate("you badword, some profane text", {})

    assert isinstance(result, FailResult)
    assert result.error_message == (
        f"Mentioned toxic words: badword; {PROFANITY_ERROR_MESSAGE}"
    )
    assert result.fix_value == ""


@pytest.mark.usefixtures("patch_slur_load")
def test_profanity_check_runs_on_redacted_text():
    validator = ContentSafety()
    profanity_mock = _set_profanity(validator, profane=False)

    validator.validate("You are a badword", {})

    checked_text = profanity_mock.call_args.args[0]
    assert checked_text == "you are a [REDACTED_SLUR]"


@pytest.mark.usefixtures("patch_slur_load")
def test_error_message_does_not_echo_input():
    text = "some profane text"
    validator = ContentSafety()
    _set_profanity(validator, profane=True)

    result = validator.validate(text, {})

    assert text not in result.error_message


@pytest.mark.usefixtures("patch_slur_load")
def test_slur_severity_forwarded():
    validator = ContentSafety(slur_severity=SlurSeverity.High)

    assert validator._slur.severity == SlurSeverity.High


@pytest.mark.usefixtures("patch_slur_load")
def test_inner_validators_use_noop_on_fail():
    validator = ContentSafety()

    assert validator._slur.on_fail_descriptor == OnFailAction.NOOP
    assert validator._profanity.on_fail_descriptor == OnFailAction.NOOP


@pytest.mark.usefixtures("patch_slur_load")
def test_rephrase_message_does_not_leak_input():
    """Profanity runs on lowercased/redacted text, so rephrase's str.replace
    can't scrub ProfanityFree's original message; ours must not contain it."""
    text = "You badword, some profane text"
    validator = ContentSafety()
    _set_profanity(validator, profane=True)

    result = validator.validate(text, {})
    rephrased = rephrase_query_on_fail(text, result)

    assert "badword" in rephrased  # slur name is part of the reason
    assert "some profane text" not in rephrased


@pytest.mark.parametrize(
    ("text", "expected_fix"),
    [
        # Profanity-first would blank all of these (ProfanityFree's fix_value is
        # always ""); slur-first redacts the slurs and keeps the rest.
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


def test_profanity_left_after_redaction_blanks_text_with_real_model():
    """'shit' isn't on the slur list, so ProfanityFree still fails the text."""
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
    ],
)
def test_clean_text_passes_with_real_model(text):
    validator = ContentSafety()

    assert isinstance(validator.validate(text, {}), PassResult)


@pytest.mark.usefixtures("patch_slur_load")
def test_guard_fix_returns_redacted_text():
    validator = ContentSafety(on_fail=OnFailAction.FIX)
    _set_profanity(validator, profane=False)

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
        assert set(kwargs.keys()) == {"slur_severity", "on_fail"}

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
