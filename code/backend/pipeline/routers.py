"""Arestas condicionais do grafo.

Funções puras: recebem estado, devolvem o nome do próximo nó. Sem I/O, sem LLM,
sem efeito colateral — por isso são testáveis diretamente e sem mock.

Este módulo é onde as regras de fluxo do squad ficam visíveis em um lugar só.
Se você precisar entender "quando o Dev é chamado de novo", a resposta está aqui
e não espalhada em sete nós.
"""

from __future__ import annotations

from typing import Literal

from domain.enums import Verdict
from pipeline.state import SquadState, latest_report


def after_dispatch(state: SquadState) -> Literal["developer", "integrate"]:
    """Tem story na fila? Trabalha. Fila vazia? Integra e fecha o run."""
    return "developer" if state.get("current_story_id") else "integrate"


def after_qa(state: SquadState, max_rework: int) -> Literal["dispatch", "developer", "escalate"]:
    """A aresta que materializa "só libera o que estiver validado".

    - Aprovada  -> `dispatch`, pega a próxima story.
    - Reprovada -> `developer`, com as `required_changes` do QA como instrução.
    - Reprovada demais -> `escalate`, pausa e chama humano em vez de queimar
      orçamento em um loop que já se mostrou improdutivo.
    """
    story_id = state.get("current_story_id")
    if not story_id:
        return "dispatch"

    report = latest_report(state, story_id)
    if report is None:
        # QA não produziu relatório: não é caso de reprovação, é falha de
        # execução. Escala — aprovar por omissão seria o pior caminho.
        return "escalate"

    if report.get("verdict") == Verdict.APPROVED.value:
        return "dispatch"

    attempts = state.get("rework", {}).get(story_id, 0)
    return "developer" if attempts < max_rework else "escalate"


def after_escalate(state: SquadState) -> Literal["developer", "dispatch", "integrate"]:
    """Depois da decisão humana vinda do `interrupt()`.

    A decisão fica em `escalations[-1]["resolution"]`:
      - `retry`  -> devolve ao Dev (orçamento estendido ou instrução nova)
      - `skip`   -> abandona a story e segue o backlog
      - `finish` -> encerra o run com o que já foi aceito
    """
    escalations = state.get("escalations", [])
    resolution = escalations[-1].get("resolution") if escalations else None

    match resolution:
        case "retry":
            return "developer"
        case "finish":
            return "integrate"
        case _:
            return "dispatch"
