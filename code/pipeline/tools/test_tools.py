"""Ferramentas de execução de testes contra code/app, usadas por Dev e QA."""
from __future__ import annotations

import subprocess
import sys
from importlib.util import find_spec

from ..config import APP_ROOT


def _run(cmd: list[str], cwd) -> str:
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=180,
        )
    except FileNotFoundError as exc:
        return f"[erro] comando não encontrado ({exc})"
    except subprocess.TimeoutExpired:
        return "[erro] execução excedeu o tempo limite (180s)"
    return (
        f"exit_code={result.returncode}\n"
        f"--- stdout ---\n{result.stdout[-6000:]}\n"
        f"--- stderr ---\n{result.stderr[-3000:]}"
    )


def run_backend_tests(rel_path: str = "backend") -> str:
    backend = APP_ROOT / rel_path
    if not backend.exists():
        return f"[erro] diretório de backend não encontrado: {rel_path}"
    if find_spec("pytest"):
        return _run([sys.executable, "-m", "pytest", "-v", "--tb=short"], cwd=backend)
    return _run([sys.executable, "-m", "unittest", "discover", "-v"], cwd=backend)


def run_frontend_tests(rel_path: str = "frontend") -> str:
    frontend = APP_ROOT / rel_path
    if not frontend.exists() or not (frontend / "package.json").exists():
        return f"[erro] projeto frontend não encontrado em: {rel_path}"
    return _run(["npm", "test", "--", "--run"], cwd=frontend)
