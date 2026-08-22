"""Único lugar que conhece Mongo, Anthropic e Docker simultaneamente (DIP,
§6). Todo o resto do sistema fala só com os ports de domain/. Trocar
AnthropicAdapter por um FakeLLM determinístico nos testes é só trocar o que
é montado aqui (LSP)."""
from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase

from .. import config
from ..agents.briefing_analyst import BriefingAnalystAgent
from ..agents.developer import DeveloperAgent
from ..agents.product_owner import ProductOwnerAgent
from ..agents.qa import QAAgent
from ..domain.enums import AgentRole
from ..infrastructure.llm.anthropic_adapter import AnthropicAdapter
from ..infrastructure.llm.budgeted_llm import BudgetedLLM
from ..infrastructure.observability.mongo_token_meter import MongoTokenMeter
from ..infrastructure.observability.sse_event_bus import InMemoryEventBus
from ..infrastructure.persistence.mongo.client import get_database
from ..infrastructure.persistence.mongo.repositories import (
    MongoADRRepository,
    MongoArtifactRepository,
    MongoMessageRepository,
    MongoRunRepository,
    MongoStoryRepository,
    MongoTestReportRepository,
)
from ..infrastructure.workspace.docker_test_runner import DockerTestRunner
from ..infrastructure.workspace.git_workspace import GitWorkspace, ReadOnlyGitWorkspace
from .agent_registry import AgentRegistry


class Container:
    def __init__(self, db: AsyncIOMotorDatabase | None = None):
        self.db = db or get_database()

        # Repositórios (um por agregado - ISP)
        self.run_repo = MongoRunRepository(self.db)
        self.story_repo = MongoStoryRepository(self.db)
        self.message_repo = MongoMessageRepository(self.db)
        self.artifact_repo = MongoArtifactRepository(self.db)
        self.adr_repo = MongoADRRepository(self.db)
        self.test_report_repo = MongoTestReportRepository(self.db)

        # Observabilidade
        self.token_meter = MongoTokenMeter(self.db)
        self.event_bus = InMemoryEventBus()

        # LLM: adapter real decorado com orçamento (OCP - BudgetedLLM não sabe
        # que fala com Anthropic, AnthropicAdapter não sabe que tem teto)
        raw_llm = AnthropicAdapter(api_key=config.ANTHROPIC_API_KEY)
        self.llm = BudgetedLLM(raw_llm, self.token_meter)

        # Workspace do Sistema B (Rivexx) + sandbox Docker (ADR-06/ADR-08)
        self.workspace = GitWorkspace(config.APP_ROOT)
        self.readonly_workspace = ReadOnlyGitWorkspace(self.workspace)
        self.test_runner = DockerTestRunner(config.APP_ROOT)

        # Agentes - cada um monta sua própria config (modelo/effort/tokens por agente, §8.4)
        self.analyst_agent = BriefingAnalystAgent(
            self.llm, self.message_repo, self.readonly_workspace,
            model=config.ANALYST_MODEL, effort=config.ANALYST_EFFORT, max_output_tokens=config.ANALYST_MAX_TOKENS,
        )
        self.po_agent = ProductOwnerAgent(
            self.llm, self.message_repo, self.readonly_workspace,
            model=config.PO_MODEL, effort=config.PO_EFFORT, max_output_tokens=config.PO_MAX_TOKENS,
        )
        self.dev_agent = DeveloperAgent(
            self.llm, self.message_repo, self.workspace, self.test_runner,
            model=config.DEV_MODEL, effort=config.DEV_EFFORT, max_output_tokens=config.DEV_MAX_TOKENS,
        )
        self.qa_agent = QAAgent(
            self.llm, self.message_repo, self.readonly_workspace, self.test_runner,
            model=config.QA_MODEL, effort=config.QA_EFFORT, max_output_tokens=config.QA_MAX_TOKENS,
        )

        self.agent_registry = AgentRegistry()
        self.agent_registry.register(AgentRole.BRIEFING_ANALYST, self.analyst_agent)
        self.agent_registry.register(AgentRole.PRODUCT_OWNER, self.po_agent)
        self.agent_registry.register(AgentRole.DEVELOPER, self.dev_agent)
        self.agent_registry.register(AgentRole.QA, self.qa_agent)
