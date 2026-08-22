"""Ports de execução — escrever código em disco e rodar teste de verdade.

Estas duas ports são o que separa "o agente falou que fez" de "o agente fez".
Sem `TestRunnerPort` executando, o "relatório de QA com evidências de aceite"
exigido pelo enunciado não existe.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from domain.entities.delivery import SourceFile
from domain.entities.quality import Evidence


@runtime_checkable
class CodeWorkspacePort(Protocol):
    """Workspace versionado onde o app gerado é escrito.

    Contrato de segurança (§11): a implementação **deve** validar cada `path`
    contra uma allowlist e recusar travessia (`..`, caminho absoluto, symlink).
    Código escrito por LLM não escolhe onde grava.
    """

    async def prepare(self, run_id: str) -> str:
        """Cria/limpa o workspace do run e devolve a raiz."""
        ...

    async def write(self, run_id: str, files: list[SourceFile]) -> list[str]:
        """Grava os arquivos e devolve os caminhos aceitos."""
        ...

    async def read(self, run_id: str, path: str) -> str: ...

    async def commit(self, run_id: str, message: str) -> str:
        """Snapshot em git. Devolve o SHA — vira evidência no Console."""
        ...

    async def export(self, run_id: str, relative_path: str, content: str) -> str:
        """Grava um entregável (backlog.md, adrs.md, qa-report.md)."""
        ...


class TestRunResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    exit_code: int
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = 0
    evidence: list[Evidence] = Field(default_factory=list)
    timed_out: bool = False

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


@runtime_checkable
class TestRunnerPort(Protocol):
    """Executa a suíte dentro do sandbox e devolve evidência material.

    Contrato de isolamento (ADR-08): sem rede host, com timeout, sem montar o
    `.env` real. Estamos rodando código escrito por LLM.
    """

    async def run_api_tests(self, run_id: str, paths: list[str]) -> TestRunResult: ...
    async def run_ui_tests(self, run_id: str, paths: list[str]) -> TestRunResult: ...
    async def run_lint(self, run_id: str) -> TestRunResult: ...
