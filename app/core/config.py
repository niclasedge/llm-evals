"""Application configuration management."""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="forbid"
    )

    # App Settings
    app_name: str = "LLM Evaluator"
    app_version: str = "1.0.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 7500

    # Database Settings
    database_url: str = "sqlite+aiosqlite:///./llm_eval.db"

    # LLM Provider Settings
    openrouter_api_key: Optional[str] = Field(None, alias="OPENROUTER_API_KEY")
    openai_api_key: Optional[str] = Field(None, alias="OPENAI_API_KEY")  # OpenAI models available via OpenRouter
    ollama_base_url: str = "http://localhost:11434"

    # Evaluation Settings
    max_concurrent_tests: int = 5
    default_timeout: int = 30
    cache_results: bool = True

    # Logging Settings
    log_level: str = "DEBUG"
    log_format: str = "json"


# Global settings instance
settings = Settings()