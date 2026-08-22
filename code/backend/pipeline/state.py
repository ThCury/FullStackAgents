"""SquadState - o contrato de integração entre agentes (§4.1). Tudo que um
agente entrega para o outro passa por aqui, e por isso é auditável de graça.

Guardamos os artefatos como dict (não como as dataclasses de domain/entities)
porque o estado precisa ser serializável pelo checkpointer do LangGraph
(AsyncMongoDBSaver) a cada transição - dataclass arbitrária complica a
serialização, dict é sempre seguro."""
from __future__ import annotations

import operator
from typing import Annotated, TypedDict


class SquadState(TypedDict):
    run_id: str
    raw_briefing: str
    brief_history: str  # resumo textual de execuções anteriores - o que torna a 2a+ execução um incremento, não uma reconstrução

    briefing: dict | None  # NormalizedBriefing.to_dict() - BriefingAnalyst
    backlog: list[dict]  # Story.to_dict()[] - PO Agent
    current_story_id: str | None

    artifacts: Annotated[list[dict], operator.add]  # Artifact.to_dict() - Dev Agent
    adrs: Annotated[list[dict], operator.add]  # ADR.to_dict() - Dev Agent
    test_reports: Annotated[list[dict], operator.add]  # TestReport.to_dict() - QA Agent
    messages: Annotated[list[dict], operator.add]  # AgentMessage.to_dict() - trilha de auditoria completa

    rework: dict[str, int]  # story_id -> nº de reprovações
    status: str  # pending|running|awaiting_human|done|failed (+ estados internos: in_dev/in_qa/integrating/resume_dev)
    escalation_reason: str | None


def initial_state(run_id: str, raw_briefing: str, brief_history: str = "") -> SquadState:
    return SquadState(
        run_id=run_id,
        raw_briefing=raw_briefing,
        brief_history=brief_history,
        briefing=None,
        backlog=[],
        current_story_id=None,
        artifacts=[],
        adrs=[],
        test_reports=[],
        messages=[],
        rework={},
        status="running",
        escalation_reason=None,
    )
