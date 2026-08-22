"""Montagem do grafo do squad (ADR-03).

    intake -> po -> dispatch -> dev -> qa -+-> dispatch (aprovada)
                        |                  |
                        |                  +-> dev      (reprovada, rework < N)
                        |                  |
                        |                  +-> escalate (reprovada demais)
                        |
                        +-> integrate -> END   (fila vazia)

Por que grafo explícito e não um loop `while`
--------------------------------------------
Três capacidades que um loop caseiro não dá de graça:

  1. **Retomada.** O checkpointer persiste o estado a cada nó. Se o run quebrar
     (rate limit, container morto, deploy no meio), `ResumeRun` continua do
     último nó — não do zero. Numa demo ao vivo é a diferença entre um soluço e
     um desastre.
  2. **`interrupt()`.** Pausar de verdade esperando decisão humana, sem manter
     processo bloqueado.
  3. **Inspeção.** O estado é um objeto consultável a cada passo, o que permite
     o Console mostrar o diff antes/depois de cada nó.

Este módulo não conhece agente concreto nem repositório: recebe os nós já
montados. Quem faz a composição é `factory/container.py`.
"""

from __future__ import annotations

from typing import Any, Protocol

from langgraph.graph import END, START, StateGraph

from pipeline import routers
from pipeline.state import SquadState


class Node(Protocol):
    """Todo nó é um callable async de estado para update parcial."""

    async def __call__(self, state: SquadState) -> dict[str, Any]: ...


def build_graph(
    *,
    intake: Node,
    product_owner: Node,
    dispatch: Node,
    developer: Node,
    qa: Node,
    escalate: Node,
    integrate: Node,
    max_rework: int = 3,
    checkpointer: Any | None = None,
) -> Any:
    """Compila o grafo. `checkpointer=None` roda sem durabilidade (útil em teste
    unitário); em produção o container injeta o saver."""
    builder = StateGraph(SquadState)

    builder.add_node("intake", intake)
    builder.add_node("product_owner", product_owner)
    builder.add_node("dispatch", dispatch)
    builder.add_node("developer", developer)
    builder.add_node("qa", qa)
    builder.add_node("escalate", escalate)
    builder.add_node("integrate", integrate)

    # Caminho linear de entrada: normalizar -> interpretar -> planejar.
    builder.add_edge(START, "intake")
    builder.add_edge("intake", "product_owner")
    builder.add_edge("product_owner", "dispatch")

    # Tem story? Trabalha. Não tem? Integra.
    builder.add_conditional_edges(
        "dispatch",
        routers.after_dispatch,
        {"developer": "developer", "integrate": "integrate"},
    )

    # Toda entrega do Dev é interceptada pelo QA. Não existe atalho.
    builder.add_edge("developer", "qa")

    # A aresta que materializa "só libera o que estiver validado".
    builder.add_conditional_edges(
        "qa",
        lambda state: routers.after_qa(state, max_rework=max_rework),
        {"dispatch": "dispatch", "developer": "developer", "escalate": "escalate"},
    )

    # Depois da decisão humana.
    builder.add_conditional_edges(
        "escalate",
        routers.after_escalate,
        {"developer": "developer", "dispatch": "dispatch", "integrate": "integrate"},
    )

    builder.add_edge("integrate", END)

    return builder.compile(checkpointer=checkpointer)
