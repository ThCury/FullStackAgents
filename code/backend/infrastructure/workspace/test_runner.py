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
        cwd = self._root / run_id
        if not cwd.is_dir():
            return TestRunResult(exit_code=1, stderr=f"workspace inexistente: {cwd}")

        env = {k: v for k in self._ENV_ALLOWLIST if (v := os.environ.get(k))}
        started = asyncio.get_running_loop().time()

        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(cwd),
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=self._timeout)
        except TimeoutError:
            process.kill()
            await process.wait()
            return TestRunResult(
                exit_code=124,
                stderr=f"timeout após {self._timeout}s: {' '.join(command)}",
                timed_out=True,
            )

        duration_ms = int((asyncio.get_running_loop().time() - started) * 1000)
        out = stdout.decode(errors="replace")

        return TestRunResult(
            exit_code=process.returncode or 0,
            stdout=out,
            stderr=stderr.decode(errors="replace"),
            duration_ms=duration_ms,
            evidence=[Evidence(kind=evidence_kind, path_or_inline=out[-4000:])],
        )
