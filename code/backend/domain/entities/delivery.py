"""Saída do Dev Agent — artefato de código + log de decisões técnicas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from domain.enums import ArtifactKind


class SourceFile(BaseModel):
    """Um arquivo escrito pelo Dev Agent.

    `path` é relativo à raiz do workspace. A `CodeWorkspacePort` valida o
    caminho contra a allowlist antes de gravar — código gerado por LLM não
    escolhe onde escreve (§11, risco "código gerado hostil").
    """

    model_config = ConfigDict(frozen=True)

    path: str
    content: str
    kind: ArtifactKind = ArtifactKind.SOURCE_CODE


class ADR(BaseModel):
    """Architecture Decision Record.

    O enunciado pede "cada decisão técnica com justificativa".
    `alternatives_considered` tem `min_length=1` porque justificativa sem
    alternativa é racionalização, não decisão (§5.2).
    """

    model_config = ConfigDict(frozen=True)

    id: str
    story_ref: str
    title: str
    context: str = Field(description="Qual força do problema exigiu a decisão")
    decision: str
    alternatives_considered: list[str] = Field(min_length=1)
    rationale: str = Field(description="Por que esta e não as alternativas")
    consequences: str = Field(description="O que passa a ser mais fácil e mais difícil")
    created_at: datetime | None = None

    def to_markdown(self) -> str:
        alts = "\n".join(f"- {a}" for a in self.alternatives_considered)
        return (
            f"## {self.id} — {self.title}\n\n"
            f"**Story:** `{self.story_ref}`\n\n"
            f"### Contexto\n{self.context}\n\n"
            f"### Decisão\n{self.decision}\n\n"
            f"### Alternativas consideradas\n{alts}\n\n"
            f"### Justificativa\n{self.rationale}\n\n"
            f"### Consequências\n{self.consequences}\n"
        )


class Artifact(BaseModel):
    """Entrega do Dev para uma story. Imutável: rework gera novo artefato.

    Manter as versões (em vez de sobrescrever) é o que permite ao Console
    mostrar a evolução após cada reprovação do QA.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    run_id: str
    story_ref: str
    attempt: int = Field(default=1, ge=1)
    files: list[SourceFile] = Field(min_length=1)
    adrs: list[ADR] = Field(default_factory=list)
    implementation_notes: str = ""
    how_to_verify: str = Field(
        default="",
        description="Como o QA deve exercitar isso — instrução do Dev para o QA",
    )
    created_at: datetime | None = None

    @property
    def file_paths(self) -> list[str]:
        return [f.path for f in self.files]
