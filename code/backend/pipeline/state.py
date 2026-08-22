"""SquadState — o contrato de integração entre agentes.

Tudo que um agente entrega para o outro passa por aqui. É por isso que a
auditoria sai de graça: não existe canal lateral entre agentes.

Duas decisões que valem entender antes de mexer
-----------------------------------------------

**1. O estado guarda `dict`, não entidades de domínio.**
O checkpointer serializa o estado a cada nó. Guardar `dict` (via
`model_dump(mode="json")`) mantém isso trivial e legível no Mongo. Os nós
convertem para entidade na entrada e de volta na saída — a fronteira é explícita
e o estado permanece inspecionável no Console sem desserializador especial.

**2. Os `Annotated[..., add]` são append-only por construção.**
Não é convenção que alguém precisa lembrar: o reducer `operator.add` concatena,
então é *impossível* um nó sobrescrever artefato ou relatório já produzido.
A trilha é imutável por estrutura de dados, não por disciplina de code review.

Campos SEM reducer (`briefing`, `current_story_id`, `rework`) usam o
comportamento padrão do LangGraph — último valor vence — porque são estado
corrente, não histórico.
"""

from __future__ import annotations

from operator import add
from typing import Annotated, Any, TypedDict


class SquadState(TypedDict, total=False):
    # --- identidade e entrada -------------------------------------------------
    run_id: str
    raw_briefing: str

    # --- produção dos agentes -------------------------------------------------
    briefing: dict[str, Any] | None
    """Saída do BriefingAnalyst: `NormalizedBriefing` serializado."""

    backlog: list[dict[str, Any]]
    """Saída do PO: stories serializadas, na ordem de prioridade."""

    queue: list[str]
    """Ids de story ainda não aceitas. `dispatch` consome, `qa` devolve em
    caso de retrabalho. Fila vazia = hora de integrar."""

    current_story_id: str | None
    """Story em trabalho. `None` só antes do primeiro dispatch e após o último."""

    artifacts: Annotated[list[dict[str, Any]], add]
    """Entregas do Dev. Append-only: retrabalho gera nova tentativa, e as
    anteriores ficam — é como o Console mostra a evolução após reprovação."""

    test_reports: Annotated[list[dict[str, Any]], add]
    """Relatórios do QA. Append-only pelo mesmo motivo."""

    adrs: Annotated[list[dict[str, Any]], add]
    """Log de decisões técnicas — entregável direto do enunciado."""

    # --- controle de fluxo ----------------------------------------------------
    rework: dict[str, int]
    """story_id -> nº de reprovações. Limite em `settings.max_rework_cycles`,
    depois `escalate`. É o que impede loop infinito Dev<->QA."""

    escalations: Annotated[list[dict[str, Any]], add]
    """Toda pausa para humano fica registrada. Intervenção humana é parte da
    trilha, não exceção invisível."""

    # --- fecho ----------------------------------------------------------------
    summary: dict[str, Any] | None
    """`RunSummary` produzido pelo `integrate`."""

    failure: str | None


def initial_state(run_id: str, raw_briefing: str) -> SquadState:
    """Estado inicial. Explícito de propósito: `total=False` no TypedDict
    facilita os updates parciais dos nós, mas deixa fácil esquecer de semear um
    campo. Todo run começa por aqui."""
    return SquadState(
        run_id=run_id,
        raw_briefing=raw_briefing,
        briefing=None,
        backlog=[],
        queue=[],
        current_story_id=None,
        artifacts=[],
        test_reports=[],
        adrs=[],
        rework={},
        escalations=[],
        summary=None,
        failure=None,
    )


def current_story(state: SquadState) -> dict[str, Any] | None:
    """Story apontada por `current_story_id`, ou `None`."""
    story_id = state.get("current_story_id")
    if not story_id:
        return None
    return next((s for s in state.get("backlog", []) if s.get("id") == story_id), None)


def latest_artifact(state: SquadState, story_id: str) -> dict[str, Any] | None:
    """Última tentativa entregue para a story — o que o QA deve avaliar."""
    matches = [a for a in state.get("artifacts", []) if a.get("story_ref") == story_id]
    return matches[-1] if matches else None


def latest_report(state: SquadState, story_id: str) -> dict[str, Any] | None:
    matches = [r for r in state.get("test_reports", []) if r.get("story_ref") == story_id]
    return matches[-1] if matches else None
