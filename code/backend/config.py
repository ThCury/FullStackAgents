from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ProviderName = Literal["fake", "openai", "gemini"]


@dataclass(frozen=True)
class AgentLLMProfile:
    """Configuração versionada escolhida por um agente."""

    provider: ProviderName
    model: str
    effort: str | None = None


@dataclass(frozen=True)
class BackendConfig:
    app_name: str = "FullStack Agents"
    persistence: Literal["memory", "mongo"] = "mongo"
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "fullstack_agents"
    stream_persist_interval_ms: int = 500
    input_token_price_per_million: Decimal = Decimal("0")
    output_token_price_per_million: Decimal = Decimal("0")
    price_version: str = "local-config-v1"


# Modelos são uma decisão versionada no código, não uma configuração secreta.
# Para trocar o PO, altere somente este perfil. DEV e QA entrarão nesta mesma lista.
AGENT_LLM_PROFILES: dict[str, AgentLLMProfile] = {
    "PRODUCT_OWNER": AgentLLMProfile(
        provider="gemini",
        model="gemini-3.6-flash",
    ),
}

BACKEND_CONFIG = BackendConfig()


def model_for_agent(role: str) -> AgentLLMProfile:
    try:
        return AGENT_LLM_PROFILES[role]
    except KeyError as error:
        raise ValueError(f"Nenhum modelo configurado para o agente {role}.") from error


class Settings(BaseSettings):
    """Somente segredos: este é o conteúdo permitido no .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GEMINI_API_KEY", "SQUAD_GEMINI_API_KEY"),
    )
    openai_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_API_KEY", "SQUAD_OPENAI_API_KEY"),
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
