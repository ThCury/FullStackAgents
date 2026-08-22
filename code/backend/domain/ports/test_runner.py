"""Port de execução de testes. A implementação real (DockerSandbox) roda
pytest/playwright dentro de um container isolado, sem rede host - ADR-08."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class TestRunResult:
    exit_code: int
    stdout: str
    stderr: str
    junit_xml: str | None = None

    @property
    def passed(self) -> bool:
        return self.exit_code == 0


class TestRunnerPort(Protocol):
    def run_backend_tests(self, rel_path: str = "backend") -> TestRunResult: ...

    def run_frontend_tests(self, rel_path: str = "frontend") -> TestRunResult: ...
