"""Schemas de saída dos agentes (structured output).

Por que "draft" e não a entidade de domínio direto
--------------------------------------------------
O LLM não gera identidade nem timestamp — quem faz isso é o `IdGeneratorPort` e
o `ClockPort`, injetados. Se pedíssemos `id` ao modelo teríamos ids inventados,
não determinísticos e não rastreáveis.

Então: o modelo devolve o *conteúdo* (draft), e o método `assemble()` do agente
promove o draft a entidade de domínio, atribuindo id e data. É a fronteira
entre "o que o LLM decide" e "o que o sistema garante".

Estes schemas viram JSON Schema via `model_json_schema()` e vão no
`output_config.format` da chamada — o que elimina retry de parsing.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from domain.entities.briefing import (
    Actor,
    Constraint,
    GlossaryTerm,
    MethodologyRef,
    OpenQuestion,
    Pain,
)
from domain.enums import ArtifactKind, Priority, ScenarioTag, TestOutcome, Verdict


class Draft(BaseModel):
    """Base dos drafts: proíbe campo extra para o structured output ser estrito."""

    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------
# BriefingAnalyst
# --------------------------------------------------------------------------
class BriefingAnalystOutput(Draft):
    """Espelha `NormalizedBriefing`.

    Note o que NÃO existe aqui: requisito, solução, prioridade, story. A
    ausência é o contrato do papel (§5.1) — o Analyst normaliza, não interpreta.
    """

    company: str
    context: str
    pains: list[Pain] = Field(min_length=1)
    constraints: list[Constraint] = Field(default_factory=list)
    actors: list[Actor] = Field(default_factory=list)
    glossary: list[GlossaryTerm] = Field(default_factory=list)
    open_questions: list[OpenQuestion] = Field(default_factory=list)
    methodology_refs: list[MethodologyRef] = Field(default_factory=list)


# --------------------------------------------------------------------------
# Product Owner
# --------------------------------------------------------------------------
class CriterionDraft(Draft):
    given: str
    when: str
    then: str


class StoryDraft(Draft):
    title: str
    narrative: str
    priority: Priority
    scenario_tag: ScenarioTag | None = None
    acceptance_criteria: list[CriterionDraft] = Field(min_length=1)
    depends_on_titles: list[str] = Field(
        default_factory=list,
        description="Títulos de outras stories. Ids são atribuídos pelo sistema.",
    )
    rationale: str


class ProductOwnerOutput(Draft):
    problem_interpretation: str
    stories: list[StoryDraft] = Field(min_length=1)
    out_of_scope: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------
# Developer
# --------------------------------------------------------------------------
class SourceFileDraft(Draft):
    path: str
    content: str
    kind: ArtifactKind = ArtifactKind.SOURCE_CODE


class AdrDraft(Draft):
    title: str
    context: str
    decision: str
    alternatives_considered: list[str] = Field(min_length=1)
    rationale: str
    consequences: str


class DeveloperOutput(Draft):
    files: list[SourceFileDraft] = Field(min_length=1)
    adrs: list[AdrDraft] = Field(min_length=1)
    implementation_notes: str = ""
    how_to_verify: str


# --------------------------------------------------------------------------
# QA
# --------------------------------------------------------------------------
class TestCaseDraft(Draft):
    criterion_ref: str
    title: str
    steps: list[str] = Field(min_length=1)
    expected: str
    outcome: TestOutcome
    actual: str
    duration_ms: int = 0


class QaOutput(Draft):
    verdict: Verdict
    cases: list[TestCaseDraft] = Field(min_length=1)
    summary: str
    rejection_reason: str | None = None
    required_changes: list[str] = Field(default_factory=list)
