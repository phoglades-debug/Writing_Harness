import anthropic
from harness.providers import LLMProvider


class AnthropicProvider(LLMProvider):
    """Anthropic Claude API client."""

    def __init__(self, api_key: str, model_name: str = "claude-3-5-sonnet-20241022"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model_name = model_name

    def generate(self, prompt: str, max_tokens: int = 4000) -> str:
        """Generate text using Claude."""
        message = self.client.messages.create(
            model=self.model_name,
            max_tokens=max_tokens,
            messages=[
                {"role": "user", "content": prompt}
            ],
        )
        return message.content[0].text
