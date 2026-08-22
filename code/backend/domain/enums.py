"""Enums do domínio. Sem dependência de framework algum."""
from __future__ import annotations

from enum import Enum


class AgentRole(str, Enum):
    BRIEFING_ANALYST = "briefing_analyst"
    PRODUCT_OWNER = "product_owner"
    DEVELOPER = "developer"
    QA = "qa"
    PIPELINE = "pipeline"  # remetente das mensagens de orquestração determinística (dispatch/escalate/integrate)


class MessageKind(str, Enum):
    HANDOFF = "handoff"       # entrega de trabalho de um agente para o próximo
    DELIVERY = "delivery"     # artefato concluído (story, código, relatório)
    REJECTION = "rejection"   # QA reprovando uma entrega do Dev
    QUESTION = "question"     # ambiguidade levantada por um agente
    DECISION = "decision"     # decisão de orquestração (ex: escalar para humano)


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_HUMAN = "awaiting_human"
    DONE = "done"
    FAILED = "failed"


class Priority(str, Enum):
    """MoSCoW."""
    MUST = "must"
    SHOULD = "should"
    COULD = "could"
    WONT = "wont"


class Verdict(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
