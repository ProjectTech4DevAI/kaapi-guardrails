from unittest.mock import patch

import pytest
from guardrails import OnFailAction
from pydantic import ValidationError

from app.core.validators.config.llamaguard_7b_safety_validator_config import (
    LlamaGuard7BSafetyValidatorConfig,
)
from app.core.validators.config.profanity_free_safety_validator_config import (
    ProfanityFreeSafetyValidatorConfig,
)
from app.core.validators.config.nsfw_text_safety_validator_config import (
    NSFWTextSafetyValidatorConfig,
)

_LLAMAGUARD_PATCH = (
    "app.core.validators.config.llamaguard_7b_safety_validator_config.LlamaGuard7B"
)
_NSFW_PATCH = "app.core.validators.config.nsfw_text_safety_validator_config.NSFWText"

_PROFANITY_PATCH = (
    "app.core.validators.config.profanity_free_safety_validator_config.ProfanityFree"
)

# ---------------------------------------------------------------------------
# LlamaGuard7B
# ---------------------------------------------------------------------------


class TestLlamaGuard7BSafetyValidatorConfig:
    def test_build_with_default_policies(self):
        config = LlamaGuard7BSafetyValidatorConfig(type="llamaguard_7b")

        with patch(_LLAMAGUARD_PATCH) as mock_validator:
            config.build()

        mock_validator.assert_called_once()
        _, kwargs = mock_validator.call_args
        assert kwargs["policies"] is None

    def test_build_with_explicit_policies(self):
        config = LlamaGuard7BSafetyValidatorConfig(
            type="llamaguard_7b",
            policies=["no_violence_hate", "no_sexual_content"],
        )

        with patch(_LLAMAGUARD_PATCH) as mock_validator:
            config.build()

        _, kwargs = mock_validator.call_args
        assert kwargs["policies"] == ["O1", "O2"]

    def test_build_with_empty_policies_list(self):
        config = LlamaGuard7BSafetyValidatorConfig(type="llamaguard_7b", policies=[])

        with patch(_LLAMAGUARD_PATCH) as mock_validator:
            config.build()

        _, kwargs = mock_validator.call_args
        assert kwargs["policies"] == []

    def test_build_with_all_policy_codes(self):
        all_policies = [
            "no_violence_hate",
            "no_sexual_content",
            "no_criminal_planning",
            "no_guns_and_illegal_weapons",
            "no_illegal_drugs",
            "no_encourage_self_harm",
        ]
        config = LlamaGuard7BSafetyValidatorConfig(
            type="llamaguard_7b", policies=all_policies
        )

        with patch(_LLAMAGUARD_PATCH) as mock_validator:
            config.build()

        _, kwargs = mock_validator.call_args
        assert kwargs["policies"] == ["O1", "O2", "O3", "O4", "O5", "O6"]

    def test_build_with_single_policy(self):
        config = LlamaGuard7BSafetyValidatorConfig(
            type="llamaguard_7b", policies=["no_criminal_planning"]
        )

        with patch(_LLAMAGUARD_PATCH) as mock_validator:
            config.build()

        _, kwargs = mock_validator.call_args
        assert kwargs["policies"] == ["O3"]

    def test_build_with_invalid_policy_raises(self):
        config = LlamaGuard7BSafetyValidatorConfig(
            type="llamaguard_7b", policies=["O1"]
        )

        with patch(_LLAMAGUARD_PATCH):
            with pytest.raises(ValueError, match="Unknown policy"):
                config.build()

    def test_build_returns_validator_instance(self):
        config = LlamaGuard7BSafetyValidatorConfig(type="llamaguard_7b")

        with patch(_LLAMAGUARD_PATCH) as mock_validator:
            result = config.build()

        assert result == mock_validator.return_value

    def test_on_fail_fix_remaps_to_exception(self):
        # LlamaGuard has no programmatic fix; on_fail=fix is silently remapped to
        # exception to prevent downstream validators from receiving None as input.
        config = LlamaGuard7BSafetyValidatorConfig(type="llamaguard_7b", on_fail="fix")

        with patch(_LLAMAGUARD_PATCH) as mock_validator:
            config.build()

        _, kwargs = mock_validator.call_args
        assert kwargs["on_fail"] == OnFailAction.EXCEPTION

    def test_on_fail_exception_resolves_to_exception_action(self):
        config = LlamaGuard7BSafetyValidatorConfig(
            type="llamaguard_7b", on_fail="exception"
        )

        with patch(_LLAMAGUARD_PATCH) as mock_validator:
            config.build()

        _, kwargs = mock_validator.call_args
        assert kwargs["on_fail"] == OnFailAction.EXCEPTION

    def test_on_fail_rephrase_resolves_to_callable(self):
        config = LlamaGuard7BSafetyValidatorConfig(
            type="llamaguard_7b", on_fail="rephrase"
        )

        with patch(_LLAMAGUARD_PATCH) as mock_validator:
            config.build()

        _, kwargs = mock_validator.call_args
        assert callable(kwargs["on_fail"])

    def test_invalid_on_fail_raises(self):
        config = LlamaGuard7BSafetyValidatorConfig(type="llamaguard_7b")
        config.on_fail = "not_a_valid_action"  # type: ignore[assignment]

        with patch(_LLAMAGUARD_PATCH):
            with pytest.raises(ValueError, match="Invalid on_fail"):
                config.build()

    def test_wrong_type_literal_rejected(self):
        with pytest.raises(ValidationError):
            LlamaGuard7BSafetyValidatorConfig(type="toxic_language")

    def test_extra_fields_rejected(self):
        with pytest.raises(ValidationError):
            LlamaGuard7BSafetyValidatorConfig(
                type="llamaguard_7b", unknown_field="value"
            )


# ---------------------------------------------------------------------------
# ProfanityFree
# ---------------------------------------------------------------------------


class TestProfanityFreeSafetyValidatorConfig:
    def test_build_default(self):
        config = ProfanityFreeSafetyValidatorConfig(type="profanity_free")

        with patch(_PROFANITY_PATCH) as mock_validator:
            config.build()

        mock_validator.assert_called_once()

    def test_build_returns_validator_instance(self):
        config = ProfanityFreeSafetyValidatorConfig(type="profanity_free")

        with patch(_PROFANITY_PATCH) as mock_validator:
            result = config.build()

        assert result == mock_validator.return_value

    def test_on_fail_fix_resolves_to_callable(self):
        config = ProfanityFreeSafetyValidatorConfig(
            type="profanity_free", on_fail="fix"
        )

        with patch(_PROFANITY_PATCH) as mock_validator:
            config.build()

        _, kwargs = mock_validator.call_args
        assert callable(kwargs["on_fail"])

    def test_on_fail_exception_resolves_to_exception_action(self):
        config = ProfanityFreeSafetyValidatorConfig(
            type="profanity_free", on_fail="exception"
        )

        with patch(_PROFANITY_PATCH) as mock_validator:
            config.build()

        _, kwargs = mock_validator.call_args
        assert kwargs["on_fail"] == OnFailAction.EXCEPTION

    def test_on_fail_rephrase_resolves_to_callable(self):
        config = ProfanityFreeSafetyValidatorConfig(
            type="profanity_free", on_fail="rephrase"
        )

        with patch(_PROFANITY_PATCH) as mock_validator:
            config.build()

        _, kwargs = mock_validator.call_args
        assert callable(kwargs["on_fail"])

    def test_invalid_on_fail_raises(self):
        config = ProfanityFreeSafetyValidatorConfig(type="profanity_free")
        config.on_fail = "not_a_valid_action"  # type: ignore[assignment]

        with patch(_PROFANITY_PATCH):
            with pytest.raises(ValueError, match="Invalid on_fail"):
                config.build()

    def test_wrong_type_literal_rejected(self):
        with pytest.raises(ValidationError):
            ProfanityFreeSafetyValidatorConfig(type="nsfw_text")

    def test_extra_fields_rejected(self):
        with pytest.raises(ValidationError):
            ProfanityFreeSafetyValidatorConfig(
                type="profanity_free", unknown_field="value"
            )

    def test_on_fix_sets_validator_metadata_when_fix_value_empty(self):
        from unittest.mock import MagicMock
        from guardrails.validators import FailResult

        config = ProfanityFreeSafetyValidatorConfig(
            type="profanity_free", on_fail="fix"
        )
        fail_result = MagicMock(spec=FailResult)
        fail_result.fix_value = ""

        config._on_fix("some input", fail_result)

        assert config.validator_metadata == {
            "reason": "Empty string has been returned since the validation failed for: profanity_free"
        }

    def test_on_fix_does_not_set_metadata_when_fix_value_present(self):
        from unittest.mock import MagicMock
        from guardrails.validators import FailResult

        config = ProfanityFreeSafetyValidatorConfig(
            type="profanity_free", on_fail="fix"
        )
        fail_result = MagicMock(spec=FailResult)
        fail_result.fix_value = "clean text"

        config._on_fix("some input", fail_result)

        assert config.validator_metadata is None

    def test_only_on_fail_forwarded_to_validator(self):
        config = ProfanityFreeSafetyValidatorConfig(
            type="profanity_free", on_fail="fix"
        )

        with patch(_PROFANITY_PATCH) as mock_validator:
            config.build()

        _, kwargs = mock_validator.call_args
        assert set(kwargs.keys()) == {"on_fail"}


# ---------------------------------------------------------------------------
# NSFWText
# ---------------------------------------------------------------------------


class TestNSFWTextSafetyValidatorConfig:
    def test_build_with_defaults(self):
        config = NSFWTextSafetyValidatorConfig(type="nsfw_text")

        with patch(_NSFW_PATCH) as mock_validator:
            config.build()

        mock_validator.assert_called_once()
        _, kwargs = mock_validator.call_args
        assert kwargs["threshold"] == 0.8
        assert kwargs["validation_method"] == "sentence"
        assert kwargs["device"] == "cpu"
        assert kwargs["model_name"] == "michellejieli/NSFW_text_classifier"

    def test_build_with_custom_params(self):
        config = NSFWTextSafetyValidatorConfig(
            type="nsfw_text",
            threshold=0.6,
            validation_method="full",
            device="cuda",
            model_name="custom/model",
        )

        with patch(_NSFW_PATCH) as mock_validator:
            config.build()

        _, kwargs = mock_validator.call_args
        assert kwargs["threshold"] == 0.6
        assert kwargs["validation_method"] == "full"
        assert kwargs["device"] == "cuda"
        assert kwargs["model_name"] == "custom/model"

    def test_build_with_threshold_at_zero(self):
        config = NSFWTextSafetyValidatorConfig(type="nsfw_text", threshold=0.0)

        with patch(_NSFW_PATCH) as mock_validator:
            config.build()

        _, kwargs = mock_validator.call_args
        assert kwargs["threshold"] == 0.0

    def test_build_with_threshold_at_one(self):
        config = NSFWTextSafetyValidatorConfig(type="nsfw_text", threshold=1.0)

        with patch(_NSFW_PATCH) as mock_validator:
            config.build()

        _, kwargs = mock_validator.call_args
        assert kwargs["threshold"] == 1.0

    def test_build_with_device_none(self):
        config = NSFWTextSafetyValidatorConfig(type="nsfw_text", device=None)

        with patch(_NSFW_PATCH) as mock_validator:
            config.build()

        _, kwargs = mock_validator.call_args
        assert kwargs["device"] is None

    def test_build_with_model_name_none(self):
        config = NSFWTextSafetyValidatorConfig(type="nsfw_text", model_name=None)

        with patch(_NSFW_PATCH) as mock_validator:
            config.build()

        _, kwargs = mock_validator.call_args
        assert kwargs["model_name"] is None

    def test_build_returns_validator_instance(self):
        config = NSFWTextSafetyValidatorConfig(type="nsfw_text")

        with patch(_NSFW_PATCH) as mock_validator:
            result = config.build()

        assert result == mock_validator.return_value

    def test_on_fail_fix_resolves_to_fix_action(self):
        config = NSFWTextSafetyValidatorConfig(type="nsfw_text", on_fail="fix")

        with patch(_NSFW_PATCH) as mock_validator:
            config.build()

        _, kwargs = mock_validator.call_args
        assert kwargs["on_fail"] == OnFailAction.FIX

    def test_on_fail_exception_resolves_to_exception_action(self):
        config = NSFWTextSafetyValidatorConfig(type="nsfw_text", on_fail="exception")

        with patch(_NSFW_PATCH) as mock_validator:
            config.build()

        _, kwargs = mock_validator.call_args
        assert kwargs["on_fail"] == OnFailAction.EXCEPTION

    def test_on_fail_rephrase_resolves_to_callable(self):
        config = NSFWTextSafetyValidatorConfig(type="nsfw_text", on_fail="rephrase")

        with patch(_NSFW_PATCH) as mock_validator:
            config.build()

        _, kwargs = mock_validator.call_args
        assert callable(kwargs["on_fail"])

    def test_invalid_on_fail_raises(self):
        config = NSFWTextSafetyValidatorConfig(type="nsfw_text")
        config.on_fail = "not_a_valid_action"  # type: ignore[assignment]

        with patch(_NSFW_PATCH):
            with pytest.raises(ValueError, match="Invalid on_fail"):
                config.build()

    def test_wrong_type_literal_rejected(self):
        with pytest.raises(ValidationError):
            NSFWTextSafetyValidatorConfig(type="toxic_language")

    def test_extra_fields_rejected(self):
        with pytest.raises(ValidationError):
            NSFWTextSafetyValidatorConfig(type="nsfw_text", unknown_field="value")

    def test_threshold_must_be_numeric(self):
        with pytest.raises(ValidationError):
            NSFWTextSafetyValidatorConfig(type="nsfw_text", threshold="high")  # type: ignore[arg-type]
