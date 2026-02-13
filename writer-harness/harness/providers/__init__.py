from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract base for LLM providers."""

    @abstractmethod
    def generate(self, prompt: str, max_tokens: int) -> str:
        """Generate text from prompt."""
        pass


def get_provider(provider_name: str, api_key: str, model_name: str):
    """Factory function to get a provider instance."""
    if provider_name.lower() == "anthropic":
        from harness.providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider(api_key=api_key, model_name=model_name)
    elif provider_name.lower() == "openai":
        from harness.providers.openai_provider import OpenAIProvider
        return OpenAIProvider(api_key=api_key, model_name=model_name)
    else:
        raise ValueError(f"Unknown provider: {provider_name}")
