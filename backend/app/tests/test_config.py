import hashlib

import pytest

from app.core.config import Settings, parse_ip_list

TOKEN_HASH = hashlib.sha256(b"test-token").hexdigest()


def _settings(**overrides) -> Settings:
    base = {
        "ENVIRONMENT": "testing",
        "PROJECT_NAME": "kaapi-guardrails-test",
        "POSTGRES_SERVER": "localhost",
        "POSTGRES_PORT": 5432,
        "POSTGRES_USER": "postgres",
        "POSTGRES_PASSWORD": "",
        "POSTGRES_DB": "test",
        "AUTH_TOKEN": TOKEN_HASH,
    }
    base.update(overrides)
    return Settings(**base)


class TestParseIpList:
    def test_single_value(self):
        assert parse_ip_list("10.0.3.14") == ["10.0.3.14"]

    def test_comma_separated_with_whitespace(self):
        assert parse_ip_list("10.0.3.14, 10.0.3.15 ,10.0.3.16") == [
            "10.0.3.14",
            "10.0.3.15",
            "10.0.3.16",
        ]

    def test_empty_string(self):
        assert parse_ip_list("") == []

    def test_blank_entries_are_dropped(self):
        assert parse_ip_list("10.0.3.14,, ,10.0.3.15") == ["10.0.3.14", "10.0.3.15"]

    def test_json_array_string_is_parsed(self):
        # A JSON-encoded env value must become a real list, never a raw string
        # that the IP check would substring-match against.
        assert parse_ip_list('["10.0.3.14", "10.0.3.15"]') == [
            "10.0.3.14",
            "10.0.3.15",
        ]

    def test_invalid_json_bracket_string_is_returned_as_is(self):
        assert parse_ip_list("[not-json") == "[not-json"

    def test_passthrough_list(self):
        assert parse_ip_list(["10.0.3.14"]) == ["10.0.3.14"]


class TestAllowedIpsSettings:
    def test_json_array_env_value_parses_to_list(self):
        settings = _settings(ALLOWED_IPS='["10.0.3.14", "10.0.3.15"]')
        assert settings.ALLOWED_IPS == ["10.0.3.14", "10.0.3.15"]

    def test_empty_disables(self):
        settings = _settings(ALLOWED_IPS="")
        assert settings.ALLOWED_IPS == []

    def test_missing_defaults_to_empty(self, monkeypatch):
        monkeypatch.delenv("ALLOWED_IPS", raising=False)
        settings = _settings()
        assert settings.ALLOWED_IPS == []

    def test_required_in_production(self):
        with pytest.raises(ValueError, match="ALLOWED_IPS"):
            _settings(ENVIRONMENT="production", ALLOWED_IPS="")
