"""Implementação de CodeWorkspacePort: leitura/escrita travada dentro de
code/app, versionada em git (ADR-06 - "arquivos em disco, versionados em
git"). Cada entrega do Dev Agent vira um commit, com a mensagem referenciando
a story - é o rastro que liga ADR -> commit -> arquivo."""
from __future__ import annotations

import subprocess
from pathlib import Path

_IGNORED_PARTS = {"node_modules", ".git", "__pycache__", "venv", ".venv", "dist", "build", ".pytest_cache"}


class GitWorkspace:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._ensure_repo()

    def _ensure_repo(self) -> None:
        if (self.root / ".git").exists():
            return
        subprocess.run(["git", "init"], cwd=self.root, capture_output=True, text=True)
        subprocess.run(["git", "config", "user.email", "squad@rivexx.local"], cwd=self.root, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Squad Dev Agent"], cwd=self.root, capture_output=True)

    def _resolve(self, rel_path: str) -> Path:
        rel_path = (rel_path or ".").strip().lstrip("/")
        target = (self.root / rel_path).resolve()
        root = self.root.resolve()
        if target != root and root not in target.parents:
            raise ValueError(f"Caminho fora de code/app não é permitido: {rel_path}")
        return target

    def read_file(self, rel_path: str) -> str:
        try:
            p = self._resolve(rel_path)
        except ValueError as exc:
            return f"[erro] {exc}"
        if not p.exists() or not p.is_file():
            return f"[erro] arquivo não encontrado: {rel_path}"
        try:
            return p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return f"[erro] arquivo binário, não é possível ler como texto: {rel_path}"

    def write_file(self, rel_path: str, content: str) -> str:
        try:
            p = self._resolve(rel_path)
        except ValueError as exc:
            return f"[erro] {exc}"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"[ok] escrito {rel_path} ({len(content)} bytes)"

    def list_dir(self, rel_path: str = ".") -> str:
        try:
            p = self._resolve(rel_path)
        except ValueError as exc:
            return f"[erro] {exc}"
        if not p.exists():
            return f"(diretório ainda não existe: {rel_path})"
        root = self.root.resolve()
        entries = []
        for item in sorted(p.rglob("*")):
            if any(part in _IGNORED_PARTS for part in item.parts):
                continue
            marker = "/" if item.is_dir() else ""
            entries.append(str(item.relative_to(root)) + marker)
        return "\n".join(entries) if entries else "(vazio)"

    def commit(self, message: str) -> str:
        subprocess.run(["git", "add", "-A"], cwd=self.root, capture_output=True, text=True)
        result = subprocess.run(
            ["git", "commit", "-m", message], cwd=self.root, capture_output=True, text=True
        )
        if result.returncode != 0:
            return ""  # nada para commitar (ex: story só de decisão, sem arquivo alterado)
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.root, capture_output=True, text=True
        ).stdout.strip()
        return sha


class ReadOnlyGitWorkspace:
    """View read-only do mesmo workspace - é isso que o BriefingAnalyst e o PO
    recebem (ISP: segregação de interface como controle de escopo do agente,
    §6). Nenhum dos dois pode chamar write_file mesmo por engano, porque o
    método não existe na classe."""

    def __init__(self, workspace: GitWorkspace):
        self._ws = workspace

    def read_file(self, rel_path: str) -> str:
        return self._ws.read_file(rel_path)

    def list_dir(self, rel_path: str = ".") -> str:
        return self._ws.list_dir(rel_path)
