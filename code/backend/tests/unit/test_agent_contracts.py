"""Contratos de papel — o `validate()` de cada agente.

Estes testes são a proteção contra o modo de falha mais insidioso do projeto: um
agente que produz algo *bem formado* mas *insuficiente*. Schema garante forma;
`validate()` garante suficiência, e é aqui que ela é verificada.
"""

from __future__ import annotations

import pytest

from agents.base import AgentDeps
from agents.briefing_analyst import BriefingAnalystAgent
from agents.product_owner import ProductOwnerAgent
from agents.qa import QaAgent
from agents.schemas import BriefingAnalystOutput, ProductOwnerOutput, QaOutput
from domain.errors import AgentContractViolation
from domain.ports.agent import AgentContext
from infrastructure.llm import fixtures
from infrastructure.llm.fake_llm import FakeLLM
from infrastructure.observability.event_bus import InMemoryEventBus
from infrastructure.persistence.memory import repositories as mem
from infrastructure.system import FrozenClock, SequentialIdGenerator


def _deps() -> AgentDeps:
    """Dependências mínimas para instanciar um agente.

    Instanciamos de verdade em vez de chamar `validate` desamarrado: o método
    usa `self.role` na mensagem de erro, e um agente meio-construído esconderia
    justamente o tipo de bug que estes testes procuram.
    """
    return AgentDeps(
        llm=FakeLLM(),
        messages=mem.InMemoryMessageRepository(),
        llm_calls=mem.InMemoryLlmCallRepository(),
        events=InMemoryEventBus(),
        ids=SequentialIdGenerator(),
        clock=FrozenClock(),
    )


def _ctx(**inputs: object) -> AgentContext:
    return AgentContext(run_id="run_1", seq=0, inputs=inputs)


# ---------------------------------------------------------------------------
# BriefingAnalyst — normaliza, não interpreta (§5.1 / ADR-07)
# ---------------------------------------------------------------------------
class TestBriefingAnalystScope:
    @pytest.fixture
    def agent(self) -> BriefingAnalystAgent:
        return BriefingAnalystAgent(_deps())

    def test_fixture_canonica_passa(self, agent: BriefingAnalystAgent) -> None:
        payload = BriefingAnalystOutput.model_validate(fixtures.BRIEFING_ANALYST)
        agent.validate(payload, _ctx())

    def test_recusa_dor_sem_verbatim(self, agent: BriefingAnalystAgent) -> None:
        """Toda dor rastreia até o texto do cliente. Sem isso o agente pode
        introduzir um problema que ninguém relatou."""
        payload = BriefingAnalystOutput.model_validate(
            {**fixtures.BRIEFING_ANALYST, "pains": [{"statement": "inventado", "verbatim": "  "}]}
        )
        with pytest.raises(AgentContractViolation, match="verbatim"):
            agent.validate(payload, _ctx())

    def test_recusa_linguagem_prescritiva(self, agent: BriefingAnalystAgent) -> None:
        """O PO é o único que interpreta o problema. Se o Analyst começa a
        escrever requisito, ele invadiu o papel — e o avaliador vai cobrar."""
        payload = BriefingAnalystOutput.model_validate(
            {
                **fixtures.BRIEFING_ANALYST,
                "context": "Como usuário, quero registrar não conformidades",
            }
        )
        with pytest.raises(AgentContractViolation, match="prescritiva"):
            agent.validate(payload, _ctx())


# ---------------------------------------------------------------------------
# Product Owner — cobertura dos 3 cenários e AC testável
# ---------------------------------------------------------------------------
class TestProductOwnerContract:
    @pytest.fixture
    def agent(self) -> ProductOwnerAgent:
        return ProductOwnerAgent(_deps())

    def test_fixture_canonica_passa(self, agent: ProductOwnerAgent) -> None:
        payload = ProductOwnerOutput.model_validate(fixtures.PRODUCT_OWNER)
        agent.validate(payload, _ctx())

    def test_recusa_backlog_sem_um_dos_cenarios(self, agent: ProductOwnerAgent) -> None:
        """Falhar aqui custa uma chamada. Descobrir no `integrate` custa o run."""
        stories = [
            s
            for s in fixtures.PRODUCT_OWNER["stories"]
            if s["scenario_tag"] != "rastreabilidade_de_lote"
        ]
        payload = ProductOwnerOutput.model_validate({**fixtures.PRODUCT_OWNER, "stories": stories})
        with pytest.raises(AgentContractViolation, match="rastreabilidade_de_lote"):
            agent.validate(payload, _ctx())

    def test_recusa_criterio_gherkin_incompleto(self, agent: ProductOwnerAgent) -> None:
        """AC sem `then` observável é teste impossível para o QA."""
        stories = [dict(s) for s in fixtures.PRODUCT_OWNER["stories"]]
        stories[0]["acceptance_criteria"] = [
            {"given": "estou logado", "when": "clico em enviar", "then": "   "}
        ]
        payload = ProductOwnerOutput.model_validate({**fixtures.PRODUCT_OWNER, "stories": stories})
        with pytest.raises(AgentContractViolation, match="Gherkin"):
            agent.validate(payload, _ctx())

    def test_assemble_resolve_dependencias_por_titulo(self, agent: ProductOwnerAgent) -> None:
        """O LLM referencia dependência por título; ids são do sistema.

        Se esta tradução quebrar, o `dispatch` libera story cuja base não existe
        e o QA reprova por motivo que não é culpa do Dev.
        """
        backlog = agent.assemble(fixtures.PRODUCT_OWNER, run_id="run_1")
        by_title = {s.title: s for s in backlog.stories}
        causa_raiz = by_title["Conduzir análise de causa raiz com sugestão baseada em histórico"]
        registro = by_title["Registrar não conformidade pelo celular na linha de produção"]

        assert causa_raiz.depends_on == [registro.id]
        assert all(c.id.startswith(registro.id) for c in registro.acceptance_criteria)


# ---------------------------------------------------------------------------
# QA — cobertura AC->caso e coerência do veredito
# ---------------------------------------------------------------------------
class TestQaContract:
    _STORY = {
        "id": "story_1",
        "acceptance_criteria": [{"id": "story_1-ac1"}, {"id": "story_1-ac2"}],
    }

    @pytest.fixture
    def agent(self) -> QaAgent:
        return QaAgent(_deps())

    def test_aprovacao_com_cobertura_completa_passa(self, agent: QaAgent) -> None:
        payload = QaOutput.model_validate(
            fixtures.qa_output(["story_1-ac1", "story_1-ac2"], approve=True)
        )
        agent.validate(payload, _ctx(story=self._STORY))

    def test_recusa_criterio_sem_caso_de_teste(self, agent: QaAgent) -> None:
        """A cadeia AC -> caso -> evidência não pode ter buraco: é o caminho que
        o avaliador vai percorrer."""
        payload = QaOutput.model_validate(fixtures.qa_output(["story_1-ac1"], approve=True))
        with pytest.raises(AgentContractViolation, match="story_1-ac2"):
            agent.validate(payload, _ctx(story=self._STORY))

    def test_recusa_aprovar_com_caso_falhando(self, agent: QaAgent) -> None:
        """Literalmente o papel do agente: "só libera o que estiver validado"."""
        data = fixtures.qa_output(["story_1-ac1", "story_1-ac2"], approve=True)
        data["cases"][0]["outcome"] = "failed"
        data["cases"][0]["actual"] = "estourou 500 no submit"
        payload = QaOutput.model_validate(data)

        with pytest.raises(AgentContractViolation, match="APPROVED"):
            agent.validate(payload, _ctx(story=self._STORY))

    def test_reprovacao_precisa_ser_acionavel(self, agent: QaAgent) -> None:
        """Reprovar sem dizer o que corrigir coloca o Dev em loop."""
        data = fixtures.qa_output(["story_1-ac1", "story_1-ac2"], approve=False)
        data["required_changes"] = []
        payload = QaOutput.model_validate(data)

        with pytest.raises(AgentContractViolation, match="required_changes"):
            agent.validate(payload, _ctx(story=self._STORY))


# ---------------------------------------------------------------------------
# As fixtures do FakeLLM precisam permanecer válidas contra os schemas
# ---------------------------------------------------------------------------
def test_fixtures_batem_com_os_schemas() -> None:
    """Guarda contra deriva silenciosa.

    Se alguém mudar um schema de agente e esquecer a fixture, o modo `fake` para
    de funcionar — e a suíte inteira mente sobre o motivo. Este teste falha
    primeiro, apontando a causa.
    """
    BriefingAnalystOutput.model_validate(fixtures.BRIEFING_ANALYST)
    ProductOwnerOutput.model_validate(fixtures.PRODUCT_OWNER)
    QaOutput.model_validate(fixtures.qa_output(["ac1", "ac2"], approve=True))
    QaOutput.model_validate(fixtures.qa_output(["ac1", "ac2"], approve=False))

    from agents.schemas import DeveloperOutput

    DeveloperOutput.model_validate(fixtures.developer_output("Título", "slug"))
    DeveloperOutput.model_validate(fixtures.developer_output("Título", "slug", rework=True))
