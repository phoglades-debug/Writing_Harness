"""Tests for harness.providers — factory + provider classes."""
import pytest
from unittest.mock import MagicMock, patch
from harness.providers import LLMProvider, get_provider


class TestGetProvider:
    def test_anthropic_provider(self):
        with patch("harness.providers.anthropic_provider.anthropic") as mock_api:
            provider = get_provider("anthropic", "sk-ant-test", "claude-3")
            from harness.providers.anthropic_provider import AnthropicProvider
            assert isinstance(provider, AnthropicProvider)

    def test_openai_provider(self):
        with patch("harness.providers.openai_provider.openai") as mock_api:
            provider = get_provider("openai", "sk-proj-test", "gpt-4")
            from harness.providers.openai_provider import OpenAIProvider
            assert isinstance(provider, OpenAIProvider)

    def test_unknown_provider(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            get_provider("llama", "key", "model")

    def test_case_insensitive(self):
        with patch("harness.providers.anthropic_provider.anthropic"):
            provider = get_provider("Anthropic", "key", "model")
            from harness.providers.anthropic_provider import AnthropicProvider
            assert isinstance(provider, AnthropicProvider)


class TestAnthropicProvider:
    def test_generate(self):
        with patch("harness.providers.anthropic_provider.anthropic") as mock_api:
            mock_client = MagicMock()
            mock_api.Anthropic.return_value = mock_client
            mock_message = MagicMock()
            mock_message.content = [MagicMock(text="Generated prose.")]
            mock_client.messages.create.return_value = mock_message

            from harness.providers.anthropic_provider import AnthropicProvider
            provider = AnthropicProvider(api_key="test-key", model_name="claude-3")
            result = provider.generate("Write something", max_tokens=100)

            assert result == "Generated prose."
            mock_client.messages.create.assert_called_once_with(
                model="claude-3",
                max_tokens=100,
                messages=[{"role": "user", "content": "Write something"}],
            )


class TestOpenAIProvider:
    def test_generate(self):
        with patch("harness.providers.openai_provider.openai") as mock_api:
            mock_client = MagicMock()
            mock_api.OpenAI.return_value = mock_client
            mock_choice = MagicMock()
            mock_choice.message.content = "GPT output."
            mock_response = MagicMock()
            mock_response.choices = [mock_choice]
            mock_client.chat.completions.create.return_value = mock_response

            from harness.providers.openai_provider import OpenAIProvider
            provider = OpenAIProvider(api_key="test-key", model_name="gpt-4")
            result = provider.generate("Write something", max_tokens=100)

            assert result == "GPT output."
            mock_client.chat.completions.create.assert_called_once_with(
                model="gpt-4",
                max_tokens=100,
                messages=[{"role": "user", "content": "Write something"}],
            )
