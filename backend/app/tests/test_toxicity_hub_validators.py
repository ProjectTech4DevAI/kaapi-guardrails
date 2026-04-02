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

_LLAMAGUARD_PATCH = (
    "app.core.validators.config.llamaguard_7b_safety_validator_config.LlamaGuard7B"
)
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
            policies=["O1", "O2"],
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
        all_policies = ["O1", "O2", "O3", "O4", "O5", "O6"]
        config = LlamaGuard7BSafetyValidatorConfig(
            type="llamaguard_7b", policies=all_policies
        )

        with patch(_LLAMAGUARD_PATCH) as mock_validator:
            config.build()

        _, kwargs = mock_validator.call_args
        assert kwargs["policies"] == all_policies

    def test_build_with_single_policy(self):
        config = LlamaGuard7BSafetyValidatorConfig(
            type="llamaguard_7b", policies=["O3"]
        )

        with patch(_LLAMAGUARD_PATCH) as mock_validator:
            config.build()

        _, kwargs = mock_validator.call_args
        assert kwargs["policies"] == ["O3"]

    def test_build_returns_validator_instance(self):
        config = LlamaGuard7BSafetyValidatorConfig(type="llamaguard_7b")

        with patch(_LLAMAGUARD_PATCH) as mock_validator:
            result = config.build()

        assert result == mock_validator.return_value

    def test_on_fail_fix_resolves_to_fix_action(self):
        config = LlamaGuard7BSafetyValidatorConfig(type="llamaguard_7b", on_fail="fix")

        with patch(_LLAMAGUARD_PATCH) as mock_validator:
            config.build()

        _, kwargs = mock_validator.call_args
        assert kwargs["on_fail"] == OnFailAction.FIX

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

    def test_on_fail_fix_resolves_to_fix_action(self):
        config = ProfanityFreeSafetyValidatorConfig(
            type="profanity_free", on_fail="fix"
        )

        with patch(_PROFANITY_PATCH) as mock_validator:
            config.build()

        _, kwargs = mock_validator.call_args
        assert kwargs["on_fail"] == OnFailAction.FIX

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

    def test_only_on_fail_forwarded_to_validator(self):
        config = ProfanityFreeSafetyValidatorConfig(
            type="profanity_free", on_fail="fix"
        )

        with patch(_PROFANITY_PATCH) as mock_validator:
            config.build()

        _, kwargs = mock_validator.call_args
        assert set(kwargs.keys()) == {"on_fail"}
