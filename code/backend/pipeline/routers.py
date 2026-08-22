"""Arestas condicionais do grafo (§4.2). Cada roteador primeiro checa se o
nó anterior sinalizou orçamento estourado (`status == "awaiting_human"`) -
BudgetExceeded nunca mata o run, sempre escala para decisão humana (§8.3)."""
from __future__ import annotations

from .. import config
from .state import SquadState


def route_after_intake(state: SquadState) -> str:
    if state.get("status") == "awaiting_human":
        return "escalate"
    return "po"


def route_after_po(state: SquadState) -> str:
    if state.get("status") == "awaiting_human":
        return "escalate"
    return "dispatch"


def route_after_dispatch(state: SquadState) -> str:
    if state.get("status") == "integrating":
        return "integrate"
    return "dev"


def route_after_dev(state: SquadState) -> str:
    if state.get("status") == "awaiting_human":
        return "escalate"
    return "qa"


def route_after_qa(state: SquadState) -> str:
    if state.get("status") == "awaiting_human":
        return "escalate"

    last_report = state["test_reports"][-1]
    if last_report["verdict"] == "approved":
        return "dispatch"

    story_id = state["current_story_id"]
    if state["rework"].get(story_id, 0) >= config.MAX_REVISIONS:
        return "escalate"
    return "dev"


def route_after_escalate(state: SquadState) -> str:
    if state.get("status") == "resume_dev":
        return "dev"
    return "__end__"
