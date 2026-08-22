"""Implementação de TestRunnerPort via container Docker isolado - ADR-08,
"não negociável": código gerado pelo Dev Agent nunca roda no host, sem rede
(--network none), com timeout. Único ponto do sistema que chama `docker`."""
from __future__ import annotations

import subprocess
from pathlib import Path

from ... import config
from ...domain.ports.test_runner import TestRunResult


class DockerTestRunner:
    def __init__(
        self,
        app_root: Path,
        backend_image: str | None = None,
        frontend_image: str | None = None,
        timeout_seconds: int | None = None,
    ):
        self.app_root = app_root
        self.backend_image = backend_image or config.DOCKER_SANDBOX_BACKEND_IMAGE
        self.frontend_image = frontend_image or config.DOCKER_SANDBOX_FRONTEND_IMAGE
        self.timeout = timeout_seconds or config.DOCKER_SANDBOX_TIMEOUT_SECONDS

    def _run(self, rel_path: str, image: str, shell_command: str) -> TestRunResult:
        workdir = (self.app_root / rel_path).resolve()
        if self.app_root.resolve() not in workdir.parents and workdir != self.app_root.resolve():
            return TestRunResult(exit_code=1, stdout="", stderr=f"caminho fora de code/app: {rel_path}")
        if not workdir.exists():
            return TestRunResult(exit_code=1, stdout="", stderr=f"diretório não encontrado: {rel_path}")

        docker_cmd = [
            "docker", "run", "--rm",
            "--network", "none",
            "-v", f"{workdir}:/workspace:rw",
            "-w", "/workspace",
            image,
            "sh", "-c", shell_command,
        ]
        try:
            result = subprocess.run(docker_cmd, capture_output=True, text=True, timeout=self.timeout)
        except subprocess.TimeoutExpired:
            return TestRunResult(exit_code=124, stdout="", stderr=f"execução excedeu o timeout ({self.timeout}s)")
        except FileNotFoundError:
            return TestRunResult(exit_code=127, stdout="", stderr="docker não encontrado no PATH")

        return TestRunResult(
            exit_code=result.returncode,
            stdout=result.stdout[-6000:],
            stderr=result.stderr[-3000:],
        )

    def run_backend_tests(self, rel_path: str = "backend") -> TestRunResult:
        cmd = (
            "pip install --quiet --no-input -r requirements.txt >/dev/null 2>&1 || true; "
            "python -m pytest -v --tb=short"
        )
        return self._run(rel_path, self.backend_image, cmd)

    def run_frontend_tests(self, rel_path: str = "frontend") -> TestRunResult:
        if not (self.app_root / rel_path / "package.json").exists():
            return TestRunResult(exit_code=1, stdout="", stderr=f"projeto frontend não encontrado em: {rel_path}")
        cmd = "npm ci --silent >/dev/null 2>&1 || npm install --silent >/dev/null 2>&1; npm test -- --run"
        return self._run(rel_path, self.frontend_image, cmd)
