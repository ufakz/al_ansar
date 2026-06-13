from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql://alansar:alansar@localhost:5432/alansar"
    gemini_api_key: str = ""
    telegram_bot_token: str = ""
    telegram_test_chat_id: str = ""

    @property
    def resolved_gemini_api_key(self) -> str:
        return self.gemini_api_key.strip().strip('"').strip("'")


settings = Settings()
