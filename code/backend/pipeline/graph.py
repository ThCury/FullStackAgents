"""Monta o SquadGraph (§4.2). O pipeline não conhece a lógica interna de
nenhum agente - recebe as instâncias já construídas (factory/container.py) e
só registra `agent.run` (via o adapter fino do nó) como nó do grafo. A única
lógica própria daqui é a orquestração determinística (dispatch/escalate/
integrate) e o roteamento condicional entre nós."""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from .nodes.dev import make_dev_node
from .nodes.dispatch import make_dispatch_node
from .nodes.escalate import make_escalate_node
from .nodes.integrate import make_integrate_node
from .nodes.intake import make_intake_node
from .nodes.po import make_po_node
from .nodes.qa import make_qa_node
from .routers import (
    route_after_dev,
    route_after_dispatch,
    route_after_escalate,
    route_after_intake,
    route_after_po,
    route_after_qa,
)
from .state import SquadState


def build_graph(container, checkpointer=None):
    """`container` é o factory/container.py já montado - expõe os agentes e
    os repositórios que os nós precisam para persistir status/mensagens."""
    graph = StateGraph(SquadState)

    graph.add_node("intake", make_intake_node(container.analyst_agent))
    graph.add_node("po", make_po_node(container.po_agent, container.story_repo))
    graph.add_node("dispatch", make_dispatch_node(container.message_repo, container.story_repo))
    graph.add_node("dev", make_dev_node(container.dev_agent, container.story_repo))
    graph.add_node("qa", make_qa_node(container.qa_agent, container.story_repo))
    graph.add_node("escalate", make_escalate_node(container.message_repo))
    graph.add_node("integrate", make_integrate_node(container.message_repo))

    graph.set_entry_point("intake")

    graph.add_conditional_edges("intake", route_after_intake, {"po": "po", "escalate": "escalate"})
    graph.add_conditional_edges("po", route_after_po, {"dispatch": "dispatch", "escalate": "escalate"})
    graph.add_conditional_edges("dispatch", route_after_dispatch, {"dev": "dev", "integrate": "integrate"})
    graph.add_conditional_edges("dev", route_after_dev, {"qa": "qa", "escalate": "escalate"})
    graph.add_conditional_edges("qa", route_after_qa, {"dispatch": "dispatch", "dev": "dev", "escalate": "escalate"})
    graph.add_conditional_edges("escalate", route_after_escalate, {"dev": "dev", "__end__": END})
    graph.add_edge("integrate", END)

    return graph.compile(checkpointer=checkpointer)
