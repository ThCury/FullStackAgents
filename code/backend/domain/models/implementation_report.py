from typing import Literal

from pydantic import BaseModel, Field


class FileChange(BaseModel):
    path: str
    action: Literal["create", "update", "delete"]


class SkippedStep(BaseModel):
    id: str
    reason: str


class ImplementationReport(BaseModel):
    summary: str
    changes: list[FileChange] = Field(default_factory=list)
    steps_completed: list[str] = Field(default_factory=list)
    steps_skipped: list[SkippedStep] = Field(default_factory=list)
    validation_commands: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)

    def divergence_from(self, actual_writes: list[dict[str, str]]) -> list[str]:
        """Compara o que o agente diz ter feito com o que foi gravado em disco.

        O disco é a verdade; o relatório é uma alegação. Divergir não invalida a
        run, mas precisa ficar registrado na auditoria.
        """
        claimed = {(change.path, change.action) for change in self.changes}
        performed = {(write["path"], write["action"]) for write in actual_writes}
        messages = [
            f"Relatado mas não gravado: {path} ({action})"
            for path, action in sorted(claimed - performed)
        ]
        messages.extend(
            f"Gravado mas não relatado: {path} ({action})"
            for path, action in sorted(performed - claimed)
        )
        return messages
