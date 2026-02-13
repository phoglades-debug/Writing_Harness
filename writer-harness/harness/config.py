import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Global settings from .env and environment."""

    provider: str = "anthropic"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    model_name: str = "claude-3-5-sonnet-20241022"
    max_tokens: int = 4000
    workspace_root: Path = Path("./workspace")

    class Config:
        env_file = ".env"
        case_sensitive = False

    def validate_provider(self):
        """Ensure provider and API key are configured."""
        if self.provider.lower() == "anthropic":
            if not self.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY not set in .env or environment")
        elif self.provider.lower() == "openai":
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY not set in .env or environment")
        else:
            raise ValueError(f"Unknown provider: {self.provider}")


settings = Settings()
