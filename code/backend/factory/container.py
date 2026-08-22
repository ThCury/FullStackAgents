"""Container de composição — o único módulo que conhece tudo.

Este é o ponto onde a inversão de dependência se paga: aqui, e só aqui,
`Mongo`, `Anthropic`, `Docker` e `LangGraph` existem simultaneamente. Nenhuma
camada interna sabe qual implementação foi escolhida.

Teste de sanidade da arquitetura: se você precisar importar algo de
`infrastructure/` em `domain/`, `application/` ou `agents/`, pare — a
dependência está invertida e o `ruff` vai barrar (regra `TID251` no
`pyproject.toml`).

Como o time usa isso
--------------------
Um dev que vai mexer em um agente não precisa ler este arquivo. Um dev que vai
**adicionar** um agente mexe em três lugares e nada mais:
  1. `agents/<novo>.py`
  2. `_build_agents()` aqui
  3. um nó em `pipeline/nodes/` + uma aresta em `pipeline/graph.py`
Nenhum agente existente é editado. É o OCP valendo na prática.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agents.base import AgentDeps
from agents.briefing_analyst import BriefingAnalystAgent
from agents.developer import DeveloperAgent
from agents.product_owner import ProductOwnerAgent
from agents.qa import QaAgent
from domain.enums import AgentRole
from domain.ports.execution import CodeWorkspacePort, TestRunnerPort
from domain.ports.llm import LLMPort
from domain.ports.observability import EventBusPort, TokenMeterPort
from domain.ports.repositories import (
    AdrRepository,
    ArtifactRepository,
    LlmCallRepository,
    MessageRepository,
    RunRepository,
    StoryRepository,
    TestReportRepository,
)
from domain.ports.system import ClockPort, IdGeneratorPort
from factory.scaffold import SCAFFOLD_CONTRACT
from factory.settings import LlmMode, PersistenceMode, SandboxMode, Settings
from infrastructure.llm.budgeted_llm import BudgetedLLM
from infrastructure.llm.fake_llm import FakeLLM
from infrastructure.observability.event_bus import InMemoryEventBus
from infrastructure.observability.token_meter import InMemoryTokenMeter
from infrastructure.persistence.memory import repositories as mem
from infrastructure.system import SystemClock, UuidGenerator
from infrastructure.workspace.local_workspace import LocalGitWorkspace
from infrastructure.workspace.test_runner import NullTestRunner, SubprocessTestRunner
from pipeline.graph import build_graph
from pipeline.nodes.agent_nodes import (
    DeveloperNode,
    IntakeNode,
    ProductOwnerNode,
    QaNode,
)
from pipeline.nodes.control_nodes import DispatchNode, EscalateNode, IntegrateNode


@dataclass(slots=True)
class Repositories:
    runs: RunRepository
    messages: MessageRepository
    llm_calls: LlmCallRepository
    stories: StoryRepository
    artifacts: ArtifactRepository
    adrs: AdrRepository
    test_reports: TestReportRepository


@dataclass(slots=True)
class Container:
    """Grafo de objetos pronto. Construído uma vez no startup da API."""

    settings: Settings
    repositories: Repositories
    llm: LLMPort
    meter: TokenMeterPort
    events: EventBusPort
    workspace: CodeWorkspacePort
    test_runner: TestRunnerPort
    clock: ClockPort
    ids: IdGeneratorPort
    graph: Any
    agents: dict[AgentRole, Any]
    mongo_client: Any | None = None

    async def aclose(self) -> None:
        if self.mongo_client is not None:
            self.mongo_client.close()


async def build_container(settings: Settings | None = None) -> Container:
    settings = settings or Settings()

    clock = SystemClock()
    ids = UuidGenerator()
    events = InMemoryEventBus()
    meter = InMemoryTokenMeter(policy=settings.budget_policy(), events=events)

    repositories, mongo_client = await _build_repositories(settings)
    llm = BudgetedLLM(_build_llm(settings), meter)
    workspace = LocalGitWorkspace(settings.workspace_root, use_git=settings.use_git)
    test_runner = _build_test_runner(settings)

    agents = _build_agents(settings, llm, repositories, events, ids, clock)
    graph = build_graph(
        intake=IntakeNode(agents[AgentRole.BRIEFING_ANALYST]),
        product_owner=ProductOwnerNode(agents[AgentRole.PRODUCT_OWNER], repositories.stories),
        dispatch=DispatchNode(repositories.messages, events, ids, clock),
        developer=DeveloperNode(
            agents[AgentRole.DEVELOPER],
            repositories.artifacts,
            repositories.adrs,
            repositories.stories,
            workspace,
            scaffold_contract=SCAFFOLD_CONTRACT,
        ),
        qa=QaNode(
            agents[AgentRole.QA], repositories.test_reports, repositories.stories, test_runner
        ),
        escalate=EscalateNode(repositories.messages, events, ids, clock, meter),
        integrate=IntegrateNode(workspace, meter, repositories.messages, events, ids, clock),
        max_rework=settings.max_rework_cycles,
        checkpointer=await _build_checkpointer(settings, mongo_client),
    )

    return Container(
        settings=settings,
        repositories=repositories,
        llm=llm,
        meter=meter,
        events=events,
        workspace=workspace,
        test_runner=test_runner,
        clock=clock,
        ids=ids,
        graph=graph,
        agents=agents,
        mongo_client=mongo_client,
    )


# ---------------------------------------------------------------------------
# Fábricas por dependência — cada uma isola UMA escolha de infraestrutura
# ---------------------------------------------------------------------------
def _build_llm(settings: Settings) -> LLMPort:
    if settings.llm is LlmMode.FAKE:
        return FakeLLM()

    # Import local: mantém o SDK da Anthropic fora do caminho de importação de
    # quem roda em modo `fake`. Um dev novo não precisa da lib instalada.
    from infrastructure.llm.anthropic_adapter import KNOWN_MODELS, AnthropicAdapter

    # Id de modelo errado só apareceria como `404 model: <id>` depois de o run
    # começar — e o provider não sugere a grafia certa. O erro mais comum é usar
    # ponto no lugar de hífen (`claude-haiku-4.5`).
    if settings.model not in KNOWN_MODELS:
        provavel = settings.model.replace(".", "-")
        dica = f" Você quis dizer '{provavel}'?" if provavel in KNOWN_MODELS else ""
        raise RuntimeError(
            f"SQUAD_MODEL='{settings.model}' não é um id conhecido.{dica} "
            f"Válidos: {', '.join(sorted(KNOWN_MODELS))}"
        )

    # Falha no startup, não no meio do primeiro run. Um `AuthenticationError`
    # vindo do quarto nó do grafo, depois de já ter gasto tempo e escrito
    # arquivo, é muito mais caro de diagnosticar do que isto.
    if not settings.anthropic_api_key:
        raise RuntimeError(
            "SQUAD_LLM=anthropic exige ANTHROPIC_API_KEY. "
            "Defina no code/backend/.env ou exporte no ambiente. "
            "Para rodar sem chave, use SQUAD_LLM=fake."
        )

    return AnthropicAdapter(model=settings.model, api_key=settings.anthropic_api_key)


async def _build_repositories(settings: Settings) -> tuple[Repositories, Any | None]:
    if settings.persistence is PersistenceMode.MEMORY:
        return (
            Repositories(
                runs=mem.InMemoryRunRepository(),
                messages=mem.InMemoryMessageRepository(),
                llm_calls=mem.InMemoryLlmCallRepository(),
                stories=mem.InMemoryStoryRepository(),
                artifacts=mem.InMemoryArtifactRepository(),
                adrs=mem.InMemoryAdrRepository(),
                test_reports=mem.InMemoryTestReportRepository(),
            ),
            None,
        )

    from motor.motor_asyncio import AsyncIOMotorClient

    from infrastructure.persistence.mongo import repositories as mongo
    from infrastructure.persistence.mongo.indexes import ensure_indexes

    client: AsyncIOMotorClient[dict[str, Any]] = AsyncIOMotorClient(settings.mongo_uri)
    db = client[settings.mongo_db]
    await ensure_indexes(db)

    return (
        Repositories(
            runs=mongo.MongoRunRepository(db),
            messages=mongo.MongoMessageRepository(db),
            llm_calls=mongo.MongoLlmCallRepository(db),
            stories=mongo.MongoStoryRepository(db),
            artifacts=mongo.MongoArtifactRepository(db),
            adrs=mongo.MongoAdrRepository(db),
            test_reports=mongo.MongoTestReportRepository(db),
        ),
        client,
    )


def _build_test_runner(settings: Settings) -> TestRunnerPort:
    match settings.sandbox:
        case SandboxMode.SUBPROCESS:
            return SubprocessTestRunner(
                settings.workspace_root, timeout=settings.test_timeout_seconds
            )
        case SandboxMode.DOCKER:
            # TODO(equipe): DockerSandboxRunner — ADR-08. Enquanto não existe,
            # cair no subprocess seria mentir sobre o isolamento; então falha alto.
            raise NotImplementedError(
                "SQUAD_SANDBOX=docker ainda não implementado (ver docs/arquitetura.md §11). "
                "Use `subprocess` em máquina de dev ou `none` para execução simulada."
            )
        case _:
            return NullTestRunner()


async def _build_checkpointer(settings: Settings, mongo_client: Any | None) -> Any:
    """Durabilidade do grafo (§4.3).

    Com Mongo disponível, o checkpointer vive no mesmo banco da auditoria — uma
    dependência a menos e um lugar só para inspecionar. Sem Mongo, `MemorySaver`
    ainda dá `interrupt()`/resume dentro do processo, o que basta para dev.
    """
    if mongo_client is not None:
        try:
            from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver

            return AsyncMongoDBSaver(mongo_client, db_name=settings.mongo_db)
        except ImportError:
            # Pacote opcional `langgraph-checkpoint-mongodb` ausente. Degrada
            # para memória em vez de derrubar a API — mas perde retomada entre
            # reinícios, então avisa alto no log.
            import logging

            logging.getLogger(__name__).warning(
                "langgraph-checkpoint-mongodb ausente: usando MemorySaver. "
                "Retomada entre reinícios do processo NÃO vai funcionar."
            )

    from langgraph.checkpoint.memory import MemorySaver

    return MemorySaver()


def _build_agents(
    settings: Settings,
    llm: LLMPort,
    repositories: Repositories,
    events: EventBusPort,
    ids: IdGeneratorPort,
    clock: ClockPort,
) -> dict[AgentRole, Any]:
    """Registry de agentes (OCP).

    Adicionar um papel novo é acrescentar uma entrada aqui. Nenhum agente
    existente é tocado — nem este dicionário precisa saber o que os outros
    fazem.
    """
    profiles = settings.agent_profiles()
    deps = AgentDeps(
        llm=llm,
        messages=repositories.messages,
        llm_calls=repositories.llm_calls,
        events=events,
        ids=ids,
        clock=clock,
    )
    return {
        AgentRole.BRIEFING_ANALYST: BriefingAnalystAgent(
            deps, profiles[AgentRole.BRIEFING_ANALYST]
        ),
        AgentRole.PRODUCT_OWNER: ProductOwnerAgent(deps, profiles[AgentRole.PRODUCT_OWNER]),
        AgentRole.DEVELOPER: DeveloperAgent(deps, profiles[AgentRole.DEVELOPER]),
        AgentRole.QA: QaAgent(deps, profiles[AgentRole.QA]),
    }
