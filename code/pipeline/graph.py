"""Montagem do grafo LangGraph do squad.

O pipeline NÃO conhece a lógica interna de nenhum agente - apenas instancia
cada classe (definida em agents/) e registra `agent.run` como nó do grafo.
A única lógica que vive aqui é a orquestração entre agentes: o roteamento
condicional que decide se uma entrega do QA volta ao Dev (retrabalho), avança
para a próxima story, ou encerra o pipeline.

Fluxo:

    START -> analyst -> po -> dev -> qa --(reprovado, ainda há tentativas)--> dev
                                       \--(aprovado ou tentativas esgotadas)--> advance
                          advance --(há próxima story)--> dev
                          advance --(backlog concluído)--> END
"""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from .agents import AnalystAgent, DevAgent, POAgent, QAAgent
from .state import PipelineState


def _advance_node(state: PipelineState) -> dict:
    """Orquestração pura do pipeline (não é um agente): avança para a próxima
    story do backlog ou marca o pipeline como concluído."""
    backlog = state["backlog"]
    next_index = state["story_index"] + 1
    if next_index < len(backlog):
        return {
            "story_index": next_index,
            "current_story_id": backlog[next_index]["id"],
            "revision_count": 0,
            "status": "in_dev",
        }
    return {"current_story_id": None, "status": "done", "revision_count": 0}


def _route_after_qa(state: PipelineState) -> str:
    last_qa = state["qa_report"][-1]
    if last_qa["approved"]:
        return "advance"
    if state["revision_count"] < state["max_revisions"]:
        return "dev"
    return "advance"  # tentativas esgotadas: escala e segue para a próxima story


def _route_after_advance(state: PipelineState) -> str:
    return "dev" if state["current_story_id"] else END


def _route_after_po(state: PipelineState) -> str:
    return "dev" if state["current_story_id"] else END


def build_graph():
    analyst = AnalystAgent()
    po = POAgent()
    dev = DevAgent()
    qa = QAAgent()

    graph = StateGraph(PipelineState)

    graph.add_node("analyst", analyst.run)
    graph.add_node("po", po.run)
    graph.add_node("dev", dev.run)
    graph.add_node("qa", qa.run)
    graph.add_node("advance", _advance_node)

    graph.set_entry_point("analyst")
    graph.add_edge("analyst", "po")
    graph.add_conditional_edges("po", _route_after_po, {"dev": "dev", END: END})
    graph.add_edge("dev", "qa")
    graph.add_conditional_edges("qa", _route_after_qa, {"dev": "dev", "advance": "advance"})
    graph.add_conditional_edges("advance", _route_after_advance, {"dev": "dev", END: END})

    return graph.compile()
