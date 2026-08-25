from functools import lru_cache
from decimal import Decimal
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="SQUAD_", extra="ignore")

    app_name: str = "FullStack Agents"
    persistence: Literal["memory", "mongo"] = "memory"
    llm_mode: Literal["fake", "openai"] = "fake"
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "fullstack_agents"
    openai_api_key: str | None = None
    openai_model: str | None = None
    openai_effort: str | None = "medium"
    input_token_price_per_million: Decimal = Decimal("0")
    output_token_price_per_million: Decimal = Decimal("0")
    price_version: str = "local-config-v1"
    stream_persist_interval_ms: int = 500


@lru_cache
def get_settings() -> Settings:
    return Settings()
