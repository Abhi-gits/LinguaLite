from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.constants import MAX_TEXT_LENGTH


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "LinguaLite"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    max_text_length: int = Field(default=MAX_TEXT_LENGTH, ge=1, le=MAX_TEXT_LENGTH)
    translation_provider: str = "ollama"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "deepseek-r1:latest"
    ollama_timeout_seconds: float = 60.0
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_timeout_seconds: float = 60.0

    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
