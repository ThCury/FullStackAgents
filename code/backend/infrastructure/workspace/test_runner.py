"""Execução da suíte de testes do app gerado.

Duas implementações, escolhidas por `SQUAD_SANDBOX`:

  `docker`     — ADR-08. Container sem rede host, com timeout, sem montar o
                 `.env` real. É o modo correto: estamos executando código
                 escrito por LLM.
  `subprocess` — fallback para ambiente sem Docker (§13, pergunta 4). Roda no
                 host com timeout e ambiente reduzido. **Garantias mais
                 fracas** — aceitável em máquina de dev, não em CI compartilhado
                 nem em máquina com credencial de produção.

`NullTestRunner` é o default do modo `fake`: não executa nada e devolve
evidência marcada como simulada. O ponto importante é que ela é **marcada**: o
Console mostra "execução simulada" em vez de fingir que rodou. Um relatório de
QA que parece real sem ser é pior que um ausente.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import time
from pathlib import Path

from domain.entities.quality import Evidence
from domain.ports.execution import TestRunResult

DEFAULT_TIMEOUT_SECONDS = 120


class NullTestRunner:
    """Não executa. Declara que não executou."""

    async def run_api_tests(self, run_id: str, paths: list[str]) -> TestRunResult:
        return self._simulated("pytest", paths)

    async def run_ui_tests(self, run_id: str, paths: list[str]) -> TestRunResult:
        return self._simulated("playwright", paths)

    async def run_lint(self, run_id: str) -> TestRunResult:
        return self._simulated("ruff", [])

    def _simulated(self, tool: str, paths: list[str]) -> TestRunResult:
        return TestRunResult(
            exit_code=0,
            stdout=f"[execução simulada] {tool} não foi executado (SQUAD_SANDBOX=none)",
            evidence=[
                Evidence(
                    kind="stdout",
                    path_or_inline=f"simulado:{tool}:{','.join(paths) or 'all'}",
                )
            ],
        )


class SubprocessTestRunner:
    """Roda no host, com timeout e ambiente reduzido.

    O ambiente é reconstruído a partir de uma allowlist em vez de herdar
    `os.environ`: sem isso, o código gerado herdaria toda credencial exportada
    no shell de quem subiu a API.
    """

    _ENV_ALLOWLIST = ("PATH", "SYSTEMROOT", "TEMP", "TMP", "LANG", "PYTHONIOENCODING")

    def __init__(self, workspace_root: Path | str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> None:
        self._root = Path(workspace_root).resolve()
        self._timeout = timeout

    async def run_api_tests(self, run_id: str, paths: list[str]) -> TestRunResult:
        return await self._run(run_id, ["python", "-m", "pytest", "-q", *paths], "junit_xml")

    async def run_ui_tests(self, run_id: str, paths: list[str]) -> TestRunResult:
        if not shutil.which("npx"):
            return TestRunResult(
                exit_code=1,
                stderr="npx indisponível — suíte de UI não pôde ser executada",
            )
        return await self._run(run_id, ["npx", "playwright", "test", *paths], "screenshot")

    async def run_lint(self, run_id: str) -> TestRunResult:
        return await self._run(run_id, ["python", "-m", "ruff", "check", "."], "stdout")

    async def _run(self, run_id: str, command: list[str], evidence_kind: str) -> TestRunResult:
        """Executa em thread, não via `asyncio.create_subprocess_exec`.

        Mesmo motivo do `LocalGitWorkspace._git`: o `WindowsSelectorEventLoop`
        que o uvicorn instala não suporta subprocesso e levanta
        `NotImplementedError` sem mensagem. `subprocess.run` em `to_thread`
        funciona em qualquer event loop, e ainda traz o `timeout=` de graça.
        """
        cwd = self._root / run_id
        if not cwd.is_dir():
            return TestRunResult(exit_code=1, stderr=f"workspace inexistente: {cwd}")

        env = {k: v for k in self._ENV_ALLOWLIST if (v := os.environ.get(k))}
        started = time.monotonic()

        try:
            result = await asyncio.to_thread(
                subprocess.run,
                command,
                cwd=str(cwd),
                env=env,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=self._timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return TestRunResult(
                exit_code=124,
                stderr=f"timeout após {self._timeout}s: {' '.join(command)}",
                duration_ms=int((time.monotonic() - started) * 1000),
                timed_out=True,
            )
        except FileNotFoundError:
            # Comando ausente no PATH. Falha explícita: o QA precisa reprovar
            # por "não pôde executar", nunca aprovar por omissão.
            return TestRunResult(exit_code=127, stderr=f"comando não encontrado: {command[0]}")

        out = result.stdout or ""
        return TestRunResult(
            exit_code=result.returncode,
            stdout=out,
            stderr=result.stderr or "",
            duration_ms=int((time.monotonic() - started) * 1000),
            evidence=[Evidence(kind=evidence_kind, path_or_inline=out[-4000:])],
        )
