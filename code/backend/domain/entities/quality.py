"""Saída do QA Agent — casos de teste executados e evidências de aceite.

Ponto central do §5.2: o QA **executa**, não opina. Por isso `TestCase` carrega
`outcome` e `evidence`, não uma "avaliação". Um caso sem execução real é
inválido (ver `QaAgent.validate`).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from domain.enums import TestOutcome, Verdict


class Evidence(BaseModel):
    """Prova material de que o caso rodou.

    Sem isso o "relatório de QA com evidências de aceite" pedido no enunciado
    não existe — vira texto gerado.
    """

    model_config = ConfigDict(frozen=True)

    kind: str = Field(description="junit_xml | screenshot | stdout | http_trace")
    path_or_inline: str
    captured_at: datetime | None = None


class TestCase(BaseModel):
    """Caso de teste amarrado a UM critério de aceite.

    `criterion_ref` é obrigatório: é o elo da cadeia
    AC -> caso -> evidência que o avaliador vai percorrer.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    criterion_ref: str
    title: str
    steps: list[str] = Field(min_length=1)
    expected: str
    outcome: TestOutcome
    actual: str = Field(description="O que de fato aconteceu na execução")
    evidence: list[Evidence] = Field(default_factory=list)
    duration_ms: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _failure_must_explain(self) -> TestCase:
        if self.outcome is TestOutcome.FAILED and not self.actual.strip():
            raise ValueError("caso reprovado precisa descrever o que aconteceu em `actual`")
        return self


class TestReport(BaseModel):
    """Veredito do QA sobre um artefato."""

    model_config = ConfigDict(frozen=True)

    id: str
    run_id: str
    story_ref: str
    artifact_ref: str
    attempt: int = Field(default=1, ge=1)
    verdict: Verdict
    cases: list[TestCase] = Field(min_length=1)
    summary: str
    rejection_reason: str | None = None
    required_changes: list[str] = Field(
        default_factory=list,
        description="Instruções acionáveis para o Dev quando reprovado",
    )
    created_at: datetime | None = None

    @model_validator(mode="after")
    def _rejection_is_actionable(self) -> TestReport:
        """Reprovar sem dizer o que corrigir garante loop infinito Dev<->QA."""
        if self.verdict is Verdict.REJECTED and not self.required_changes:
            raise ValueError("reprovação exige ao menos uma mudança requerida")
        return self

    @property
    def covered_criteria(self) -> set[str]:
        return {c.criterion_ref for c in self.cases}

    @property
    def passed(self) -> int:
        return sum(1 for c in self.cases if c.outcome is TestOutcome.PASSED)

    @property
    def failed(self) -> int:
        return sum(1 for c in self.cases if c.outcome is TestOutcome.FAILED)
