"""Tests for harness.config — Settings management."""
import pytest
from harness.config import Settings


class TestSettings:
    def test_defaults(self):
        s = Settings(
            _env_file=None,
            provider="anthropic",
            anthropic_api_key="",
            openai_api_key="",
        )
        assert s.provider == "anthropic"
        assert s.max_tokens == 4000
        assert s.model_name == "claude-3-5-sonnet-20241022"

    def test_validate_provider_anthropic_missing_key(self):
        s = Settings(
            _env_file=None,
            provider="anthropic",
            anthropic_api_key="",
        )
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            s.validate_provider()

    def test_validate_provider_anthropic_ok(self):
        s = Settings(
            _env_file=None,
            provider="anthropic",
            anthropic_api_key="sk-ant-test",
        )
        s.validate_provider()  # should not raise

    def test_validate_provider_openai_missing_key(self):
        s = Settings(
            _env_file=None,
            provider="openai",
            openai_api_key="",
        )
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            s.validate_provider()

    def test_validate_provider_openai_ok(self):
        s = Settings(
            _env_file=None,
            provider="openai",
            openai_api_key="sk-proj-test",
        )
        s.validate_provider()  # should not raise

    def test_validate_provider_unknown(self):
        s = Settings(
            _env_file=None,
            provider="llama",
        )
        with pytest.raises(ValueError, match="Unknown provider"):
            s.validate_provider()
