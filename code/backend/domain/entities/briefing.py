"""Saída do BriefingAnalyst — o problema tornado legível.

Contrato de escopo (§5.1 da arquitetura): este agente **normaliza, não
interpreta**. O PO Agent continua sendo o único ponto de contato com o problema
do cliente, conforme exige o enunciado da Trilha B.

Por isso não existe aqui nenhum campo de requisito, solução ou prioridade — a
ausência é o contrato. Adicionar um campo desses transfere responsabilidade do
PO para o Analyst e quebra a divisão de papéis.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ConstraintKind(StrEnum):
    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"
    COMPLIANCE = "compliance"


class Constraint(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: ConstraintKind
    statement: str
    verbatim: str = Field(description="Trecho literal do briefing que originou a restrição")


class Pain(BaseModel):
    """Uma dor relatada. `verbatim` é obrigatório: rastreia a dor até o texto do
    cliente e impede o agente de inventar problema."""

    model_config = ConfigDict(frozen=True)

    statement: str
    verbatim: str
    impact: str | None = None


class Actor(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    responsibility: str


class GlossaryTerm(BaseModel):
    model_config = ConfigDict(frozen=True)

    term: str
    definition: str


class OpenQuestion(BaseModel):
    """Gap ou ambiguidade detectada.

    O Analyst **levanta** a pergunta; não a responde. Vira input do PO e
    aparece no Console para o avaliador ver o squad reconhecendo incerteza em
    vez de alucinar certeza.
    """

    model_config = ConfigDict(frozen=True)

    question: str
    why_it_matters: str
    blocks_scenarios: list[str] = Field(default_factory=list)


class MethodologyRef(BaseModel):
    """Referência metodológica anexada como *material*, não como escolha.

    Quem decide qual metodologia usar é o PO/Dev.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    applies_to: str
    summary: str


class NormalizedBriefing(BaseModel):
    """Briefing cru transformado em estrutura consultável."""

    model_config = ConfigDict(frozen=True)

    company: str
    context: str
    pains: list[Pain] = Field(min_length=1)
    constraints: list[Constraint] = Field(default_factory=list)
    actors: list[Actor] = Field(default_factory=list)
    glossary: list[GlossaryTerm] = Field(default_factory=list)
    open_questions: list[OpenQuestion] = Field(default_factory=list)
    methodology_refs: list[MethodologyRef] = Field(default_factory=list)
