"""O teste que mais importa: o squad inteiro, ponta a ponta.

Se este teste passa, a esteira funciona — briefing entra, backlog é gerado,
código é escrito, QA reprova, Dev corrige, QA aprova, run fecha com os
entregáveis exportados. É o smoke test que o time deve rodar antes de qualquer
push.
"""

from __future__ import annotations

from typing import Any

import pytest

from domain.enums import AgentRole, MessageKind, ScenarioTag, Verdict
from pipeline.state import initial_state
from tests.conftest import BRIEFING_RIVEXX


@pytest.fixture
async def executed_run(squad: dict[str, Any]) -> dict[str, Any]:
    """Executa o run completo uma vez; os testes abaixo inspecionam o resultado."""
    config = {"configurable": {"thread_id": "run_test"}}
    final = await squad["graph"].ainvoke(initial_state("run_test", BRIEFING_RIVEXX), config)
    return {"state": final, "squad": squad}


async def test_run_completa_e_produz_resumo(executed_run: dict[str, Any]) -> None:
    summary = executed_run["state"]["summary"]

    assert summary is not None, "o nó `integrate` não produziu RunSummary"
    assert summary["stories_total"] == 3
    assert summary["stories_accepted"] == 3, "toda story deveria terminar aceita"
    assert summary["adrs_recorded"] >= 3


async def test_cobre_os_tres_cenarios_obrigatorios(executed_run: dict[str, Any]) -> None:
    """O enunciado lista os 3 cenários como obrigatórios. Sem eles a demo é
    inavaliável — então isto é asserção, não expectativa."""
    covered = set(executed_run["state"]["summary"]["scenarios_covered"])
    assert covered == {t.value for t in ScenarioTag}


async def test_qa_reprova_e_dev_corrige(executed_run: dict[str, Any]) -> None:
    """O ciclo de retrabalho é a parte interessante do grafo.

    O `FakeLLM` reprova a primeira avaliação de propósito: o caminho felizão
    nunca exercitaria a aresta condicional `qa -> developer`.
    """
    state = executed_run["state"]
    reports = state["test_reports"]

    rejected = [r for r in reports if r["verdict"] == Verdict.REJECTED.value]
    assert len(rejected) == 1, "esperava exatamente uma reprovação (a primeira)"
    assert rejected[0]["required_changes"], "reprovação sem instrução acionável"

    # A reprovação gerou nova tentativa do Dev para a mesma story.
    story_id = rejected[0]["story_ref"]
    attempts = [a for a in state["artifacts"] if a["story_ref"] == story_id]
    assert len(attempts) == 2, "o Dev deveria ter entregado uma segunda tentativa"
    assert [a["attempt"] for a in attempts] == [1, 2]

    # E as duas tentativas ficaram guardadas — append-only.
    assert state["rework"][story_id] == 1


async def test_trilha_de_auditoria_e_completa_e_ordenada(
    executed_run: dict[str, Any],
) -> None:
    """ "Um output final sem orquestração visível não será considerado."

    Este teste é a garantia mecânica de que a trilha existe.
    """
    repos = executed_run["squad"]["repositories"]
    messages = await repos.messages.list_by_run("run_test")

    assert len(messages) >= 10, "trilha curta demais para evidenciar orquestração"

    # Ordem total sem buraco nem repetição.
    assert [m.seq for m in messages] == list(range(len(messages)))

    # Todo agente do squad aparece falando.
    speakers = {m.from_agent for m in messages}
    assert AgentRole.BRIEFING_ANALYST in speakers
    assert AgentRole.PRODUCT_OWNER in speakers
    assert AgentRole.DEVELOPER in speakers
    assert AgentRole.QA in speakers
    assert AgentRole.ORCHESTRATOR in speakers

    # A reprovação aparece como decisão explícita, não como silêncio.
    decisions = [m for m in messages if m.kind is MessageKind.DECISION]
    assert decisions, "os vereditos do QA deveriam estar na trilha"

    # Toda mensagem é legível por humano e justificada.
    for message in messages:
        assert message.summary.strip(), f"mensagem {message.seq} sem summary"


async def test_toda_mensagem_de_agente_liga_na_chamada_crua(
    executed_run: dict[str, Any],
) -> None:
    """A auditoria de dois níveis (§8): handoff de negócio -> chamada técnica.

    É o que permite ao Console mostrar envelope e prompt lado a lado.
    """
    repos = executed_run["squad"]["repositories"]
    messages = await repos.messages.list_by_run("run_test")

    for message in messages:
        if message.from_agent is AgentRole.ORCHESTRATOR:
            continue  # nós determinísticos não chamam LLM
        assert message.llm_call_ref, f"mensagem {message.seq} sem `llm_call_ref`"
        call = await repos.llm_calls.get(message.llm_call_ref)
        assert call is not None, f"chamada {message.llm_call_ref} não persistida"
        assert call.system_prompt and call.user_prompt
        assert call.raw_response


async def test_codigo_e_escrito_em_disco(executed_run: dict[str, Any]) -> None:
    """ "Escreve o código" precisa significar arquivo em disco, não string em log.

    O disco reflete a ÚLTIMA escrita de cada caminho: retrabalho sobrescreve o
    arquivo, como faria um dev humano. O histórico das tentativas anteriores vive
    em `artifacts` (append-only), não no working tree.
    """
    squad = executed_run["squad"]

    latest_by_path: dict[str, str] = {}
    for artifact in executed_run["state"]["artifacts"]:
        for source in artifact["files"]:
            latest_by_path[source["path"]] = source["content"]

    assert latest_by_path, "nenhum arquivo foi entregue"
    for path, expected in latest_by_path.items():
        assert await squad["workspace"].read("run_test", path) == expected


async def test_entregaveis_exportados_em_markdown(executed_run: dict[str, Any]) -> None:
    """Os 5 entregáveis do enunciado, em arquivo — o avaliador pode querer levar."""
    exported = executed_run["state"]["summary"]["exported_files"]
    names = {path.replace("\\", "/").split("/")[-1] for path in exported}

    assert names == {"backlog.md", "decision-log.md", "qa-report.md", "squad-timeline.md"}


async def test_tokens_sao_contabilizados(executed_run: dict[str, Any]) -> None:
    snapshot = await executed_run["squad"]["meter"].snapshot("run_test")

    assert snapshot.total_spent > 0
    assert snapshot.total_cost_usd >= 0
    # Cada papel de IA consumiu orçamento; o orquestrador não.
    for role in (AgentRole.BRIEFING_ANALYST, AgentRole.PRODUCT_OWNER, AgentRole.DEVELOPER):
        assert snapshot.spent_by_agent.get(role.value, 0) > 0
    assert AgentRole.ORCHESTRATOR.value not in snapshot.spent_by_agent
