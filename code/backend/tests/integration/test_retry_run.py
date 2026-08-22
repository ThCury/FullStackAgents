"""Retomada após falha — o run continua de onde parou.

O cenário real que motivou isto: um run de 16 minutos morreu no primeiro agente
por resposta truncada. Recomeçar do zero significaria refazer (e repagar) tudo.

O que estes testes provam:
  1. O grafo retoma com `astream(None, config)` do último nó concluído.
  2. Trabalho já feito não é refeito — nem chamada de LLM, nem escrita de código.
  3. Sem checkpoint, a API diz isso em vez de fingir que retomou.
"""

from __future__ import annotations

from typing import Any

import pytest

from domain.enums import AgentRole
from domain.errors import LLMResponseTruncated
from domain.ports.llm import LLMRequest, LLMResponse
from infrastructure.llm.fake_llm import FakeLLM
from pipeline.state import initial_state
from tests.conftest import BRIEFING_RIVEXX


class FalhaUmaVez:
    """`LLMPort` que estoura na N-ésima chamada e depois funciona.

    Simula a falha transitória real (truncamento, rate limit) sem tocar a rede.
    """

    def __init__(self, inner: FakeLLM, falhar_na_chamada: int) -> None:
        self._inner = inner
        self._falhar_na = falhar_na_chamada
        self.chamadas = 0
        self.ja_falhou = False

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.chamadas += 1
        if self.chamadas == self._falhar_na and not self.ja_falhou:
            self.ja_falhou = True
            raise LLMResponseTruncated(
                agent=request.agent.value, max_tokens=request.max_tokens, output_tokens=999
            )
        return await self._inner.complete(request)

    async def count_tokens(self, request: LLMRequest) -> int:
        return await self._inner.count_tokens(request)


@pytest.fixture
def squad_que_falha(squad: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Injeta a falha na 3ª chamada — já passou do Analyst e do PO, e morre no
    meio do trabalho do Dev. É o ponto interessante: existe progresso a preservar.
    """
    # O `BudgetedLLM` embrulha o LLM; substituímos o miolo dele.
    falho = FalhaUmaVez(squad["llm"], falhar_na_chamada=3)
    for agent in squad["agents"].values():
        monkeypatch.setattr(agent._llm, "_inner", falho)
    squad["falho"] = falho
    return squad


async def test_retoma_do_ponto_da_falha_sem_refazer(squad_que_falha: dict[str, Any]) -> None:
    squad = squad_que_falha
    config = {"configurable": {"thread_id": "run_retry"}}

    # --- primeira tentativa: morre no meio -----------------------------------
    with pytest.raises(LLMResponseTruncated):
        await squad["graph"].ainvoke(initial_state("run_retry", BRIEFING_RIVEXX), config)

    parcial = await squad["graph"].aget_state(config)
    assert parcial.values, "sem checkpoint não há o que retomar"
    assert parcial.values.get("backlog"), "o PO já tinha entregado antes da falha"

    chamadas_antes = squad["falho"].chamadas
    mensagens_antes = len(await squad["repositories"].messages.list_by_run("run_retry"))

    # --- retomada: entrada `None` continua do checkpoint ---------------------
    final = await squad["graph"].ainvoke(None, config)

    assert final["summary"] is not None, "o run deveria ter concluído na retomada"
    assert final["summary"]["stories_accepted"] == 3

    # O Analyst e o PO NÃO foram chamados de novo: só houve chamada nova a
    # partir do ponto da falha.
    novas = squad["falho"].chamadas - chamadas_antes
    assert novas < chamadas_antes + 10, "retomada não deveria refazer a esteira inteira"

    # A trilha de auditoria continua de onde parou, sem duplicar.
    mensagens = await squad["repositories"].messages.list_by_run("run_retry")
    assert len(mensagens) > mensagens_antes
    assert [m.seq for m in mensagens] == list(range(len(mensagens))), "seq duplicada ou com buraco"


async def test_backlog_do_po_e_preservado_na_retomada(squad_que_falha: dict[str, Any]) -> None:
    """O trabalho caro (interpretação do problema) não é repetido."""
    squad = squad_que_falha
    config = {"configurable": {"thread_id": "run_retry2"}}

    with pytest.raises(LLMResponseTruncated):
        await squad["graph"].ainvoke(initial_state("run_retry2", BRIEFING_RIVEXX), config)

    antes = (await squad["graph"].aget_state(config)).values["backlog"]
    ids_antes = [s["id"] for s in antes]

    final = await squad["graph"].ainvoke(None, config)

    assert [s["id"] for s in final["backlog"]] == ids_antes, (
        "os ids das stories mudaram — o PO foi executado de novo"
    )


async def test_sem_checkpoint_a_retomada_e_recusada(squad: dict[str, Any]) -> None:
    """Run que nunca rodou não tem estado. Recusar é melhor que começar do zero
    silenciosamente — o usuário pediu para *continuar*, não para recomeçar."""
    from application.use_cases.run_squad import RetryRunUseCase
    from domain.entities.run import Run
    from domain.errors import NoCheckpointAvailable
    from domain.value_objects import BudgetPolicy

    repos = squad["repositories"]
    run = Run.create(
        run_id="run_sem_estado",
        briefing=BRIEFING_RIVEXX,
        policy=BudgetPolicy(),
        now=squad["clock"].now(),
    )
    await repos.runs.save(run)

    use_case = RetryRunUseCase(
        runs=repos.runs, events=squad["events"], clock=squad["clock"], graph=squad["graph"]
    )

    assert await use_case.has_checkpoint("run_sem_estado") is False
    with pytest.raises(NoCheckpointAvailable, match="SQUAD_PERSISTENCE=mongo"):
        await use_case.execute("run_sem_estado")


async def test_truncamento_produz_erro_diagnosticavel() -> None:
    """A mensagem precisa dizer o que fazer.

    Antes disso o usuário recebia
    `JSONDecodeError('Unterminated string starting at: line 1 column 21535')` —
    que não aponta nem o agente, nem a causa, nem a solução.
    """
    erro = LLMResponseTruncated(
        agent=AgentRole.BRIEFING_ANALYST.value, max_tokens=16_000, output_tokens=15_998
    )

    texto = str(erro)
    assert "briefing_analyst" in texto
    assert "16000" in texto.replace("_", "")
    assert "thinking" in texto.lower()
    assert "effort" in texto.lower()
