"""Workspace local versionado em git.

Segurança (ADR-08 / §11): estamos gravando conteúdo escrito por um LLM. Todo
caminho passa por `_safe_path`, que recusa:
  - caminho absoluto
  - travessia (`..`)
  - qualquer resolução que caia fora da raiz do run
  - link simbólico já existente no destino

A validação é feita por `Path.resolve()` e comparação de prefixo real, não por
inspeção de string — checar `".." in path` sozinho é contornável (`a/./../../x`,
separador do Windows, encoding).

Nada aqui executa código. Execução é responsabilidade do `TestRunnerPort`, que
roda em sandbox isolado.
"""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from domain.entities.delivery import SourceFile


class LocalGitWorkspace:
    def __init__(self, root: Path | str, use_git: bool = True) -> None:
        self._root = Path(root).resolve()
        self._use_git = use_git

    def run_root(self, run_id: str) -> Path:
        return self._root / run_id

    async def prepare(self, run_id: str) -> str:
        path = self.run_root(run_id)
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True)
        if self._use_git:
            await self._git(path, "init", "--quiet")
        return str(path)

    async def write(self, run_id: str, files: list[SourceFile]) -> list[str]:
        base = self.run_root(run_id)
        base.mkdir(parents=True, exist_ok=True)

        written: list[str] = []
        for file in files:
            target = self._safe_path(base, file.path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(file.content, encoding="utf-8")
            written.append(file.path)
        return written

    async def read(self, run_id: str, path: str) -> str:
        return self._safe_path(self.run_root(run_id), path).read_text(encoding="utf-8")

    async def commit(self, run_id: str, message: str) -> str:
        """Snapshot em git. O SHA vira evidência de entrega no Console."""
        if not self._use_git:
            return ""
        path = self.run_root(run_id)
        await self._git(path, "add", "-A")
        await self._git(
            path,
            "-c",
            "user.name=Squad Agent",
            "-c",
            "user.email=squad@localhost",
            "commit",
            "--quiet",
            "--allow-empty",
            "-m",
            message,
        )
        return (await self._git(path, "rev-parse", "HEAD")).strip()

    async def export(self, run_id: str, relative_path: str, content: str) -> str:
        target = self._safe_path(self.run_root(run_id), relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return str(target)

    # ------------------------------------------------------------------ interno
    def _safe_path(self, base: Path, relative: str) -> Path:
        candidate = Path(relative)
        if candidate.is_absolute():
            raise ValueError(f"caminho absoluto recusado: {relative}")

        resolved_base = base.resolve()
        target = (resolved_base / candidate).resolve()

        if not target.is_relative_to(resolved_base):
            raise ValueError(f"caminho escapa do workspace: {relative}")
        if target.is_symlink():
            raise ValueError(f"link simbólico recusado: {relative}")
        return target

    async def _git(self, cwd: Path, *args: str) -> str:
        process = await asyncio.create_subprocess_exec(
            "git",
            *args,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} falhou: {stderr.decode(errors='replace')}")
        return stdout.decode(errors="replace")
