from unittest.mock import ANY, MagicMock, patch

import pandas as pd
import pytest
from guardrails import Guard, OnFailAction
from guardrails.validators import FailResult, PassResult
from pydantic import ValidationError

from app.core.constants import (
    CONTENT_SAFETY_DEFAULT_FALLBACK_MESSAGE,
    REPHRASE_ON_FAIL_PREFIX,
)
from app.core.enum import SlurSeverity
from app.core.on_fail_actions import rephrase_query_on_fail
from app.core.validators import content_safety
from app.core.validators.config.content_safety_safety_validator_config import (
    ContentSafetySafetyValidatorConfig,
)
from app.core.validators.content_safety import (
    DEFAULT_MODEL_NAME,
    DEFAULT_TOXIC_LABEL,
    DEFAULT_TOXICITY_THRESHOLD,
    TOXICITY_ERROR_MESSAGE,
    ContentSafety,
)
from app.core.validators.lexical_slur import LexicalSlur

_LOAD_PIPELINE_PATCH = "app.core.validators.content_safety._load_pipeline"
_CONTENT_SAFETY_PATCH = (
    "app.core.validators.config.content_safety_safety_validator_config.ContentSafety"
)
FALLBACK = "Please rephrase your message without abusive language."
HINDI_FALLBACK = "कृपया अपना संदेश अपमानजनक भाषा के बिना दोबारा लिखें।"
_COMPLETION_PATCH = "app.core.validators.content_safety.completion"


# ---------------------------------------
# Fixtures
# ---------------------------------------
@pytest.fixture(autouse=True)
def no_llm_key(monkeypatch):
    """No API key by default, so localize_fallback returns the English text and no
    test reaches the network. Translation tests set a key and mock completion."""
    monkeypatch.setattr(content_safety.settings, "OPENAI_API_KEY", None)


@pytest.fixture
def translator(monkeypatch):
    monkeypatch.setattr(content_safety.settings, "OPENAI_API_KEY", "test-key")
    response = MagicMock()
    response.choices[0].message.content = f"  {HINDI_FALLBACK}\n"
    with patch(_COMPLETION_PATCH, return_value=response) as mock_completion:
        yield mock_completion


@pytest.fixture
def patch_slur_load(monkeypatch):
    """Use a tiny fixed slur list instead of the curated CSV."""

    def fake_load_slur_list(_self):
        df = pd.DataFrame({"label": ["badword", "highslur"], "severity": ["L", "H"]})
        return df["label"].str.lower().tolist()

    monkeypatch.setattr(LexicalSlur, "load_slur_list", fake_load_slur_list)


@pytest.fixture
def toxicity_score():
    """Stub the HF pipeline so tests don't load the model. Set `.score = x` to
    control the toxic-label probability; defaults to clean. `.calls` records the
    texts scored."""
    fake = MagicMock()
    fake.score = 0.0
    fake.calls = []

    def run(text, **_kwargs):
        fake.calls.append(text)
        return [
            {"label": "LABEL_0", "score": 1 - fake.score},
            {"label": "LABEL_1", "score": fake.score},
        ]

    fake.side_effect = run
    with patch(_LOAD_PIPELINE_PATCH, return_value=fake):
        yield fake


@pytest.fixture
def real_validator():
    """ContentSafety on the real slur list and the real textdetox model; skipped
    when the model is not available locally (no network / cache)."""
    try:
        return ContentSafety()
    except OSError as exc:  # HF raises OSError when the model can't be fetched
        pytest.skip(f"model unavailable: {exc}")


TOXIC = 0.97


# ---------------------------------------
# ContentSafety validator
# ---------------------------------------
@pytest.mark.usefixtures("patch_slur_load", "toxicity_score")
def test_passes_clean_text():
    validator = ContentSafety()

    result = validator.validate("This is a perfectly fine sentence", {})

    assert isinstance(result, PassResult)


@pytest.mark.usefixtures("patch_slur_load", "toxicity_score")
def test_slur_only_is_redacted():
    validator = ContentSafety()

    result = validator.validate("You are a BADWORD", {})

    assert isinstance(result, FailResult)
    assert result.error_message == "Mentioned toxic words: badword"
    assert result.fix_value == "you are a [REDACTED_SLUR]"


@pytest.mark.usefixtures("patch_slur_load")
def test_toxic_text_returns_fallback_message(toxicity_score):
    validator = ContentSafety(fallback_message=FALLBACK)
    toxicity_score.score = TOXIC

    result = validator.validate("some abusive text", {})

    assert isinstance(result, FailResult)
    assert result.error_message == f"{TOXICITY_ERROR_MESSAGE} (score 0.97)"
    assert result.fix_value == FALLBACK


@pytest.mark.usefixtures("patch_slur_load")
def test_toxic_text_uses_default_fallback(toxicity_score):
    validator = ContentSafety()
    toxicity_score.score = TOXIC

    result = validator.validate("some abusive text", {})

    assert result.fix_value == CONTENT_SAFETY_DEFAULT_FALLBACK_MESSAGE


@pytest.mark.usefixtures("patch_slur_load")
def test_toxic_fallback_is_translated_to_query_language(toxicity_score, translator):
    validator = ContentSafety(fallback_message=FALLBACK)
    toxicity_score.score = TOXIC

    result = validator.validate("tu bahut ganda hai", {})

    assert result.fix_value == HINDI_FALLBACK
    _, kwargs = translator.call_args
    assert FALLBACK in kwargs["messages"][0]["content"]
    assert kwargs["messages"][1] == {"role": "user", "content": "tu bahut ganda hai"}


@pytest.mark.usefixtures("patch_slur_load")
def test_translation_failure_returns_english_fallback(toxicity_score, translator):
    translator.side_effect = RuntimeError("boom")
    validator = ContentSafety(fallback_message=FALLBACK)
    toxicity_score.score = TOXIC

    result = validator.validate("tu bahut ganda hai", {})

    assert result.fix_value == FALLBACK


@pytest.mark.usefixtures("patch_slur_load")
def test_slur_only_does_not_call_translator(toxicity_score, translator):
    validator = ContentSafety(fallback_message=FALLBACK)

    validator.validate("You are a BADWORD", {})

    translator.assert_not_called()


@pytest.mark.usefixtures("patch_slur_load")
def test_toxic_text_without_fallback_returns_rephrase_prefix(toxicity_score):
    validator = ContentSafety(fallback_message=None)
    toxicity_score.score = TOXIC

    result = validator.validate("some abusive text", {})

    assert isinstance(result, FailResult)
    assert result.fix_value == REPHRASE_ON_FAIL_PREFIX


@pytest.mark.usefixtures("patch_slur_load")
def test_slur_and_toxicity_combines_errors(toxicity_score):
    validator = ContentSafety(fallback_message=FALLBACK)
    toxicity_score.score = TOXIC

    result = validator.validate("you badword, some abusive text", {})

    assert isinstance(result, FailResult)
    assert result.error_message == (
        f"Mentioned toxic words: badword; {TOXICITY_ERROR_MESSAGE} (score 0.97)"
    )
    assert result.fix_value == FALLBACK


@pytest.mark.usefixtures("patch_slur_load")
def test_model_scores_original_text(toxicity_score):
    """Redacting first would hide the signal from the classifier."""
    validator = ContentSafety()

    validator.validate("You are a badword", {})

    assert toxicity_score.calls == ["You are a badword"]


@pytest.mark.usefixtures("patch_slur_load")
def test_error_message_does_not_echo_input(toxicity_score):
    text = "some abusive text"
    validator = ContentSafety()
    toxicity_score.score = TOXIC

    result = validator.validate(text, {})

    assert text not in result.error_message


@pytest.mark.usefixtures("patch_slur_load", "toxicity_score")
def test_slur_severity_forwarded():
    validator = ContentSafety(slur_severity=SlurSeverity.High)

    assert validator._slur.severity == SlurSeverity.High


@pytest.mark.usefixtures("patch_slur_load", "toxicity_score")
def test_inner_slur_validator_uses_noop_on_fail():
    validator = ContentSafety()

    assert validator._slur.on_fail_descriptor == OnFailAction.NOOP


@pytest.mark.parametrize(
    ("score", "threshold", "fails"),
    [
        (0.49, DEFAULT_TOXICITY_THRESHOLD, False),
        (0.5, DEFAULT_TOXICITY_THRESHOLD, True),  # threshold is inclusive
        (0.97, DEFAULT_TOXICITY_THRESHOLD, True),
        (0.6, 0.7, False),
        (0.95, 0.99, False),
    ],
)
@pytest.mark.usefixtures("patch_slur_load")
def test_toxicity_threshold(toxicity_score, score, threshold, fails):
    validator = ContentSafety(threshold=threshold)
    toxicity_score.score = score

    result = validator.validate("some text", {})

    assert isinstance(result, FailResult) is fails


@pytest.mark.usefixtures("patch_slur_load")
def test_custom_toxic_label(toxicity_score):
    toxicity_score.side_effect = lambda text, **_: [
        {"label": "neutral", "score": 0.1},
        {"label": "toxic", "score": 0.9},
    ]
    validator = ContentSafety(toxic_label="toxic")

    result = validator.validate("some text", {})

    assert isinstance(result, FailResult)


@pytest.mark.usefixtures("patch_slur_load")
def test_missing_toxic_label_raises(toxicity_score):
    """A model that never emits `toxic_label` must not silently pass everything."""
    validator = ContentSafety(toxic_label="toxic")

    with pytest.raises(ValueError, match="toxic_label"):
        validator.validate("some text", {})


@pytest.mark.usefixtures("patch_slur_load")
def test_pipeline_loaded_once_per_model(monkeypatch):
    content_safety._load_pipeline.cache_clear()
    loads = []

    def fake_hf_pipeline(_task, model, **_kwargs):
        loads.append(model)
        return MagicMock()

    import transformers

    monkeypatch.setattr(transformers, "pipeline", fake_hf_pipeline)
    try:
        ContentSafety(model_name="m1")
        ContentSafety(model_name="m1")
        ContentSafety(model_name="m2")
    finally:
        content_safety._load_pipeline.cache_clear()

    assert loads == ["m1", "m2"]


@pytest.mark.usefixtures("patch_slur_load")
def test_rephrase_message_does_not_leak_input(toxicity_score):
    """rephrase's str.replace can only scrub the exact input; our error message
    must never contain user text in any form."""
    text = "You badword, some abusive text"
    validator = ContentSafety()
    toxicity_score.score = TOXIC

    result = validator.validate(text, {})
    rephrased = rephrase_query_on_fail(text, result)

    assert "badword" in rephrased  # slur name is part of the reason
    assert "some abusive text" not in rephrased


@pytest.mark.usefixtures("patch_slur_load", "toxicity_score")
def test_guard_fix_returns_redacted_text():
    validator = ContentSafety(on_fail=OnFailAction.FIX)

    outcome = Guard().use(validator).validate("You are a badword")

    assert outcome.validated_output == "you are a [REDACTED_SLUR]"


# ---------------------------------------
# Real model (skipped when the HF model is not available locally)
# ---------------------------------------
@pytest.mark.parametrize(
    "text",
    [
        "tu chutiya hai bhag yahan se",  # slur + hostile context
        "madrachod ki tere ko koi rokta nahin hai",  # variant not in the CSV
        "purane gano ko kharab mat karo pahle kapde pahne sikh lo nangi aurat",
    ],
)
def test_toxic_text_fails_with_real_model(real_validator, text):
    result = real_validator.validate(text, {})

    assert isinstance(result, FailResult)
    assert TOXICITY_ERROR_MESSAGE in result.error_message
    assert result.fix_value == CONTENT_SAFETY_DEFAULT_FALLBACK_MESSAGE


@pytest.mark.parametrize(
    "text",
    [
        "Please share the vaccination schedule for my child",
        "mujhe help chahiye",
        "मुझे स्कूल की फीस के बारे में जानकारी चाहिए",
        # Hinglish that the old English profanity model false-flagged.
        "namaste, kaise ho",
        "aap kaise ho",
        "kya ho raha hai",
        "tu kahan hai",
    ],
)
def test_clean_text_passes_with_real_model(real_validator, text):
    assert isinstance(real_validator.validate(text, {}), PassResult)


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
        assert kwargs == {
            "slur_severity": SlurSeverity.All,
            "threshold": DEFAULT_TOXICITY_THRESHOLD,
            "model_name": DEFAULT_MODEL_NAME,
            "toxic_label": DEFAULT_TOXIC_LABEL,
            "fallback_message": CONTENT_SAFETY_DEFAULT_FALLBACK_MESSAGE,
            "on_fail": ANY,
        }

    def test_model_fields_forwarded(self):
        config = ContentSafetySafetyValidatorConfig(
            type="content_safety",
            slur_severity="high",
            threshold=0.7,
            model_name="textdetox/xlmr-large-toxicity-classifier",
            toxic_label="toxic",
            fallback_message=FALLBACK,
        )

        with patch(_CONTENT_SAFETY_PATCH) as mock_validator:
            config.build()

        _, kwargs = mock_validator.call_args
        assert kwargs["slur_severity"] == SlurSeverity.High
        assert kwargs["threshold"] == 0.7
        assert kwargs["model_name"] == "textdetox/xlmr-large-toxicity-classifier"
        assert kwargs["toxic_label"] == "toxic"
        assert kwargs["fallback_message"] == FALLBACK

    @pytest.mark.parametrize("threshold", [-0.1, 1.5])
    def test_out_of_range_threshold_rejected(self, threshold):
        with pytest.raises(ValidationError):
            ContentSafetySafetyValidatorConfig(
                type="content_safety", threshold=threshold
            )

    def test_profanity_threshold_no_longer_accepted(self):
        with pytest.raises(ValidationError):
            ContentSafetySafetyValidatorConfig(
                type="content_safety", profanity_threshold=0.9
            )

    def test_empty_fallback_message_rejected(self):
        with pytest.raises(ValidationError):
            ContentSafetySafetyValidatorConfig(
                type="content_safety", fallback_message=""
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

    def test_rephrase_with_fallback_returns_fallback(self):
        config = ContentSafetySafetyValidatorConfig(
            type="content_safety", on_fail="rephrase", fallback_message=FALLBACK
        )
        fail_result = FailResult(
            error_message="Mentioned toxic words: badword", fix_value="redacted"
        )

        assert config.resolve_on_fail()("some text", fail_result) == FALLBACK

    def test_rephrase_toxic_reuses_translated_fix_value(self, translator):
        config = ContentSafetySafetyValidatorConfig(
            type="content_safety", on_fail="rephrase", fallback_message=FALLBACK
        )
        fail_result = FailResult(
            error_message=f"{TOXICITY_ERROR_MESSAGE} (score 0.97)",
            fix_value=HINDI_FALLBACK,
        )

        assert config.resolve_on_fail()("some text", fail_result) == HINDI_FALLBACK
        translator.assert_not_called()

    def test_rephrase_slur_only_translates_fallback(self, translator):
        config = ContentSafetySafetyValidatorConfig(
            type="content_safety", on_fail="rephrase"
        )
        fail_result = FailResult(
            error_message="Mentioned toxic words: badword", fix_value="redacted"
        )

        assert config.resolve_on_fail()("tu badword", fail_result) == HINDI_FALLBACK
        _, kwargs = translator.call_args
        assert (
            CONTENT_SAFETY_DEFAULT_FALLBACK_MESSAGE in kwargs["messages"][0]["content"]
        )

    def test_rephrase_without_fallback_uses_prefix(self):
        config = ContentSafetySafetyValidatorConfig(
            type="content_safety", on_fail="rephrase", fallback_message=None
        )
        fail_result = FailResult(error_message=TOXICITY_ERROR_MESSAGE, fix_value="")

        reply = config.resolve_on_fail()("some text", fail_result)

        assert reply.startswith(REPHRASE_ON_FAIL_PREFIX)
        assert TOXICITY_ERROR_MESSAGE in reply

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

    def test_on_fix_returns_fallback_when_set(self):
        config = ContentSafetySafetyValidatorConfig(
            type="content_safety", on_fail="fix", fallback_message=FALLBACK
        )
        fail_result = MagicMock(spec=FailResult)
        fail_result.fix_value = FALLBACK

        assert config._on_fix("some input", fail_result) == FALLBACK
        assert config._validator_metadata is None
