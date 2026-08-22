"""Fixtures compartilhadas.

Princípio: **nenhum teste toca rede, Mongo ou Docker.** O squad inteiro roda com
`FakeLLM` + repositórios em memória + relógio congelado + ids sequenciais. Isso
torna a suíte rápida e determinística, e é o que permite testar a trilha de
auditoria por igualdade exata.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from agents.base import AgentDeps
from agents.briefing_analyst import BriefingAnalystAgent
from agents.developer import DeveloperAgent
from agents.product_owner import ProductOwnerAgent
from agents.qa import QaAgent
from domain.enums import AgentRole
from factory.scaffold import SCAFFOLD_CONTRACT
from factory.settings import Settings
from infrastructure.llm.budgeted_llm import BudgetedLLM
from infrastructure.llm.fake_llm import FakeLLM
from infrastructure.observability.event_bus import InMemoryEventBus
from infrastructure.observability.token_meter import InMemoryTokenMeter
from infrastructure.persistence.memory import repositories as mem
from infrastructure.system import FrozenClock, SequentialIdGenerator
from infrastructure.workspace.local_workspace import LocalGitWorkspace
from infrastructure.workspace.test_runner import NullTestRunner
from pipeline.graph import build_graph
from pipeline.nodes.agent_nodes import DeveloperNode, IntakeNode, ProductOwnerNode, QaNode
from pipeline.nodes.control_nodes import DispatchNode, EscalateNode, IntegrateNode

BRIEFING_RIVEXX = """
Empresa: Rivexx Componentes. Indústria de componentes plásticos de alta precisão,
2 plantas, fornecimento para automotivo e eletroeletrônico. 480 colaboradores,
operação em 3 turnos. Toda não conformidade detectada desencadeia investigação
manual: quem operou, qual lote, qual matéria-prima, qual equipamento. A informação
existe mas está espalhada em registros físicos, planilhas e memória de pessoas.
Precisamos de uma aplicação web interna que centralize o registro de não
conformidades, conduza análise de causa raiz e permita rastrear qualquer lote em
segundos.
""".strip()


@pytest.fixture
def clock() -> FrozenClock:
    return FrozenClock(step_seconds=1)


@pytest.fixture
def ids() -> SequentialIdGenerator:
    return SequentialIdGenerator()


@pytest.fixture
def events() -> InMemoryEventBus:
    return InMemoryEventBus()


class Repos:
    """Conjunto de repositórios em memória, com a mesma forma do `Repositories`
    do container — para os testes montarem nós sem depender do container."""

    def __init__(self) -> None:
        self.runs = mem.InMemoryRunRepository()
        self.messages = mem.InMemoryMessageRepository()
        self.llm_calls = mem.InMemoryLlmCallRepository()
        self.stories = mem.InMemoryStoryRepository()
        self.artifacts = mem.InMemoryArtifactRepository()
        self.adrs = mem.InMemoryAdrRepository()
        self.test_reports = mem.InMemoryTestReportRepository()


@pytest.fixture
def repositories() -> Repos:
    return Repos()


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
def squad(
    tmp_path: Path,
    clock: FrozenClock,
    ids: SequentialIdGenerator,
    events: InMemoryEventBus,
    repositories: Repos,
    fake_llm: FakeLLM,
) -> dict[str, Any]:
    """Squad completo montado à mão, sem o container.

    Montar explicitamente (em vez de chamar `build_container`) deixa o teste
    dizer exatamente qual implementação está em jogo — e falha de forma óbvia se
    alguém adicionar uma dependência nova a um agente.
    """
    meter = InMemoryTokenMeter(events=events)
    llm = BudgetedLLM(fake_llm, meter)
    workspace = LocalGitWorkspace(tmp_path / "ws", use_git=False)
    runner = NullTestRunner()

    deps = AgentDeps(
        llm=llm,
        messages=repositories.messages,
        llm_calls=repositories.llm_calls,
        events=events,
        ids=ids,
        clock=clock,
    )
    analyst = BriefingAnalystAgent(deps)
    product_owner = ProductOwnerAgent(deps)
    developer = DeveloperAgent(deps)
    qa_agent = QaAgent(deps)
    agents = {
        AgentRole.BRIEFING_ANALYST: analyst,
        AgentRole.PRODUCT_OWNER: product_owner,
        AgentRole.DEVELOPER: developer,
        AgentRole.QA: qa_agent,
    }

    graph = build_graph(
        intake=IntakeNode(analyst),
        product_owner=ProductOwnerNode(product_owner, repositories.stories),
        dispatch=DispatchNode(repositories.messages, events, ids, clock),
        developer=DeveloperNode(
            developer,
            repositories.artifacts,
            repositories.adrs,
            repositories.stories,
            workspace,
            scaffold_contract=SCAFFOLD_CONTRACT,
        ),
        qa=QaNode(qa_agent, repositories.test_reports, repositories.stories, runner),
        escalate=EscalateNode(repositories.messages, events, ids, clock, meter),
        integrate=IntegrateNode(workspace, meter, repositories.messages, events, ids, clock),
        max_rework=3,
    )

    return {
        "graph": graph,
        "agents": agents,
        "repositories": repositories,
        "meter": meter,
        "events": events,
        "workspace": workspace,
        "llm": fake_llm,
        "clock": clock,
        "ids": ids,
    }


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(workspace_root=tmp_path / "ws", use_git=False)
