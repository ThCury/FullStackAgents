"""Saída do PO Agent — o backlog. Entregável explícito da Trilha B."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from domain.enums import Priority, ScenarioTag, StoryStatus
from domain.value_objects import AcceptanceCriterion


class Story(BaseModel):
    """User story priorizada com critérios de aceite testáveis.

    `acceptance_criteria` tem `min_length=1` de propósito: story sem AC não é
    testável, e story não testável trava o QA Agent. O contrato é validado no
    `ProductOwnerAgent.validate()`.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    title: str = Field(min_length=5)
    narrative: str = Field(description="Como <ator>, quero <ação>, para <valor>")
    priority: Priority
    scenario_tag: ScenarioTag | None = Field(
        default=None,
        description="Amarra a story a um dos 3 cenários obrigatórios da demo",
    )
    acceptance_criteria: list[AcceptanceCriterion] = Field(min_length=1)
    depends_on: list[str] = Field(default_factory=list)
    rationale: str = Field(description="Por que esta prioridade — justifica o MoSCoW")
    status: StoryStatus = StoryStatus.BACKLOG

    def with_status(self, status: StoryStatus) -> Story:
        return self.model_copy(update={"status": status})

    @property
    def is_terminal(self) -> bool:
        return self.status in (StoryStatus.ACCEPTED, StoryStatus.BLOCKED)


class Backlog(BaseModel):
    """Coleção ordenada de stories + a leitura que o PO fez do problema."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    stories: list[Story] = Field(min_length=1)
    problem_interpretation: str = Field(
        description="Leitura do PO sobre o problema — o único agente autorizado a fazê-la"
    )
    out_of_scope: list[str] = Field(
        default_factory=list,
        description="O que o PO decidiu NÃO fazer. Escopo negativo é decisão e deve ser auditável.",
    )
    created_at: datetime | None = None

    def covered_scenarios(self) -> set[ScenarioTag]:
        return {s.scenario_tag for s in self.stories if s.scenario_tag is not None}

    def ordered(self) -> list[Story]:
        """Ordem de execução: prioridade MoSCoW, respeitando dependências."""
        rank = {Priority.MUST: 0, Priority.SHOULD: 1, Priority.COULD: 2, Priority.WONT: 3}
        return sorted(self.stories, key=lambda s: (rank[s.priority], len(s.depends_on)))
