"""Typed settings loaded from environment / `.env` (repo root)."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    database_url: SecretStr

    gemini_api_key: SecretStr
    gemini_model: str = "gemini-3.1-flash-lite"
    gemini_price_input_per_m: float = Field(ge=0)
    gemini_price_output_per_m: float = Field(ge=0)
    gemini_batch_size: int = Field(default=15, ge=1, le=50)
    gemini_min_interval_s: float = 4.5  # stay under free-tier RPM limits
    max_tag_per_run: int = 1500  # hard cost ceiling per run

    http_user_agent: str = "BeepTracker/0.1"
    http_timeout_s: float = 20.0

    # Optional until the web app is deployed.
    revalidate_url: str | None = None
    revalidate_secret: SecretStr | None = None

    def llm_cost_usd(self, input_tokens: int, output_tokens: int) -> float:
        return (
            input_tokens * self.gemini_price_input_per_m
            + output_tokens * self.gemini_price_output_per_m
        ) / 1_000_000


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
