"""Configuração — tudo por variável de ambiente, nada hardcoded.

Os defaults são escolhidos para o **dia zero de um dev novo**: clonar, instalar
e rodar. Por isso `llm=fake` e `persistence=memory` são o padrão — nenhuma API
key, nenhum Mongo, nenhum Docker necessário para ver a esteira funcionando.

Ligar o modo real é mudar duas variáveis. Ver README.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from domain.enums import AgentRole, Effort
from domain.value_objects import AgentBudgetProfile, BudgetPolicy


class LlmMode(StrEnum):
    FAKE = "fake"
    ANTHROPIC = "anthropic"


class PersistenceMode(StrEnum):
    MEMORY = "memory"
    MONGO = "mongo"


class SandboxMode(StrEnum):
    NONE = "none"
    SUBPROCESS = "subprocess"
    DOCKER = "docker"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SQUAD_", env_file=".env", extra="ignore")

    app_name: str = "FullStackAgents Squad API"

    # --- modos de operação ----------------------------------------------------
    llm: LlmMode = LlmMode.FAKE
    persistence: PersistenceMode = PersistenceMode.MEMORY
    sandbox: SandboxMode = SandboxMode.NONE

    # --- modelo ---------------------------------------------------------------
    model: str = "claude-opus-5"
    anthropic_api_key: str | None = None

    # --- Mongo ----------------------------------------------------------------
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "squad_db"

    # --- workspace ------------------------------------------------------------
    workspace_root: Path = Path("./.workspaces")
    use_git: bool = True

    # --- fluxo ----------------------------------------------------------------
    max_rework_cycles: int = Field(
        default=3,
        ge=1,
        description="Reprovações na mesma story antes de escalar para humano",
    )
    test_timeout_seconds: int = Field(default=120, ge=5)

    # --- orçamento ------------------------------------------------------------
    budget_per_run: int = Field(default=2_000_000, gt=0)
    budget_per_agent: int = Field(default=800_000, gt=0)
    budget_per_call: int = Field(default=200_000, gt=0)

    # --- CORS -----------------------------------------------------------------
    cors_origins: list[str] = Field(default=["http://localhost:5173"])

    def budget_policy(self) -> BudgetPolicy:
        return BudgetPolicy(
            per_run=self.budget_per_run,
            per_agent=self.budget_per_agent,
            per_call=self.budget_per_call,
        )

    def agent_profiles(self) -> dict[AgentRole, AgentBudgetProfile]:
        """Effort por papel — o dial de custo do ADR-05.

        Não trocamos de modelo para economizar; ajustamos o effort. O Dev pesa
        mais porque codegen é a tarefa mais sensível a capacidade; Analyst e QA
        têm trabalho mais estruturado e rodam em `medium` sem perda observável.

        Se for calibrar, meça antes: o painel de tokens do Console mostra custo
        por agente.
        """
        return {
            AgentRole.BRIEFING_ANALYST: AgentBudgetProfile(effort=Effort.MEDIUM, max_tokens=16_000),
            AgentRole.PRODUCT_OWNER: AgentBudgetProfile(effort=Effort.HIGH, max_tokens=32_000),
            AgentRole.DEVELOPER: AgentBudgetProfile(effort=Effort.XHIGH, max_tokens=64_000),
            AgentRole.QA: AgentBudgetProfile(effort=Effort.MEDIUM, max_tokens=32_000),
        }
