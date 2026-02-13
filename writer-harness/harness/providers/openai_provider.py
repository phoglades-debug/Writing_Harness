import openai
from harness.providers import LLMProvider


class OpenAIProvider(LLMProvider):
    """OpenAI GPT API client."""

    def __init__(self, api_key: str, model_name: str = "gpt-4-turbo"):
        self.client = openai.OpenAI(api_key=api_key)
        self.model_name = model_name

    def generate(self, prompt: str, max_tokens: int = 4000) -> str:
        """Generate text using GPT."""
        response = self.client.chat.completions.create(
            model=self.model_name,
            max_tokens=max_tokens,
            messages=[
                {"role": "user", "content": prompt}
            ],
        )
        return response.choices[0].message.content
