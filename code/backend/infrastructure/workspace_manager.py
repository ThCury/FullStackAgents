from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

IGNORED_DIRECTORIES = {".git", "node_modules", "__pycache__", "dist", ".venv", ".pytest_cache"}
MAX_READ_CHARS = 60_000
MAX_WRITE_CHARS = 400_000
TRUNCATION_NOTICE = "\n\n[... arquivo truncado para leitura ...]"


class UnavailableWorkspaceManager:
    """Adia a falha de configuração até uma run realmente precisar do DEV."""

    _MESSAGE = (
        "DEV_WORKSPACE_ROOT é obrigatório para executar o agente DEV. "
        "Defina uma pasta local dedicada no arquivo .env."
    )

    def create_project(self, run_id: str, project_name: str) -> dict:
        raise ValueError(self._MESSAGE)

    def open_project_workspace(self, workspace: dict) -> dict:
        raise RuntimeError(self._MESSAGE)

    def template_manifest(self) -> str:
        raise RuntimeError(self._MESSAGE)

    def code_tree(self, workspace: dict) -> list[str]:
        raise RuntimeError(self._MESSAGE)

    def read_code(self, workspace: dict, path: str) -> str:
        raise RuntimeError(self._MESSAGE)

    def write_code(self, workspace: dict, path: str, content: str) -> Path:
        raise RuntimeError(self._MESSAGE)

    def delete_code(self, workspace: dict, path: str) -> None:
        raise RuntimeError(self._MESSAGE)

    def diff(self, workspace: dict) -> str:
        raise RuntimeError(self._MESSAGE)

    def write_artifact(self, workspace: dict, filename: str, content: str) -> Path:
        raise RuntimeError(self._MESSAGE)


class LocalWorkspaceManager:
    """Cria workspaces confinados a uma raiz local autorizada.

    Toda operação de arquivo é validada contra a pasta da própria run, e não
    apenas contra a raiz: um caminho vindo do modelo não pode alcançar o
    workspace de outra run.
    """

    def __init__(self, root: Path, template_root: Path) -> None:
        self._root = root.resolve()
        self._template_root = template_root.resolve()
        if not self._template_root.is_dir():
            raise ValueError(f"Template não encontrado: {self._template_root}")

    def create_project(self, run_id: str, project_name: str) -> dict:
        self._root.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^a-z0-9-]+", "-", project_name.lower()).strip("-") or "project"
        suffix = run_id.removeprefix("run_")[:8]
        workspace_path = self._contain(self._root, self._root / f"{slug}_{suffix}")
        if workspace_path.exists():
            raise ValueError(f"Workspace já existe: {workspace_path.name}")
        code_path = workspace_path / "codigo"
        artifacts_path = workspace_path / "artifacts"
        shutil.copytree(
            self._template_root,
            code_path,
            ignore=shutil.ignore_patterns(".env", "node_modules", "dist"),
        )
        artifacts_path.mkdir(parents=True)
        return {
            "workspace_path": str(workspace_path),
            "code_path": str(code_path),
            "artifacts_path": str(artifacts_path),
            "template": "code/template",
            "baseline_commit": self._create_baseline(code_path),
        }

    def open_project_workspace(self, workspace: dict) -> dict:
        """Valida e devolve um workspace persistente de um único projeto."""
        code_path = self._code_root(workspace)
        artifacts_path = Path(workspace["artifacts_path"]).resolve()
        self._contain(self._root, artifacts_path)
        if not code_path.is_dir() or not artifacts_path.is_dir():
            raise ValueError("Workspace do projeto não existe mais no disco.")
        return {
            **workspace,
            "workspace_path": str(Path(workspace["workspace_path"]).resolve()),
            "code_path": str(code_path),
            "artifacts_path": str(artifacts_path),
        }

    def template_manifest(self) -> str:
        return (self._template_root / "docs" / "agent-manifest.md").read_text(encoding="utf-8")

    def code_tree(self, workspace: dict) -> list[str]:
        code_path = self._code_root(workspace)
        paths: list[str] = []
        for entry in code_path.rglob("*"):
            if not entry.is_file():
                continue
            relative = entry.relative_to(code_path)
            if IGNORED_DIRECTORIES & set(relative.parts):
                continue
            paths.append(relative.as_posix())
        return sorted(paths)

    def read_code(self, workspace: dict, path: str) -> str:
        target = self._code_file(workspace, path)
        if not target.is_file():
            raise FileNotFoundError(f"Arquivo inexistente no workspace: {path}")
        try:
            content = target.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            raise ValueError(f"Arquivo binário não pode ser lido como texto: {path}") from error
        if len(content) > MAX_READ_CHARS:
            return content[:MAX_READ_CHARS] + TRUNCATION_NOTICE
        return content

    def write_code(self, workspace: dict, path: str, content: str) -> Path:
        if len(content) > MAX_WRITE_CHARS:
            raise ValueError(f"Conteúdo excede {MAX_WRITE_CHARS} caracteres: {path}")
        target = self._code_file(workspace, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
        return target

    def delete_code(self, workspace: dict, path: str) -> None:
        target = self._code_file(workspace, path)
        if not target.is_file():
            raise FileNotFoundError(f"Arquivo inexistente no workspace: {path}")
        target.unlink()

    def diff(self, workspace: dict) -> str:
        code_path = self._code_root(workspace)
        if not (code_path / ".git").is_dir():
            return ""
        self._git(code_path, "add", "-A")
        result = self._git(code_path, "diff", "--cached", "--stat")
        return result.stdout if result else ""

    def write_artifact(self, workspace: dict, filename: str, content: str) -> Path:
        artifacts_root = Path(workspace["artifacts_path"]).resolve()
        self._contain(self._root, artifacts_root)
        target = self._contain(artifacts_root, artifacts_root / filename)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def _code_root(self, workspace: dict) -> Path:
        code_path = Path(workspace["code_path"]).resolve()
        self._contain(self._root, code_path)
        return code_path

    def _code_file(self, workspace: dict, path: str) -> Path:
        code_path = self._code_root(workspace)
        candidate = path.strip().replace("\\", "/")
        if not candidate or candidate.startswith("/") or Path(candidate).is_absolute():
            raise ValueError(f"Use um caminho relativo a raiz do codigo: {path!r}")
        return self._contain(code_path, code_path / candidate)

    def _create_baseline(self, code_path: Path) -> str | None:
        """Baseline em git dá diff e rollback de graça; git ausente não é fatal."""
        if self._git(code_path, "init", "--quiet") is None:
            return None
        self._git(code_path, "add", "-A")
        self._git(
            code_path,
            "-c",
            "user.name=FullStack Agents",
            "-c",
            "user.email=agents@local",
            "commit",
            "--quiet",
            "-m",
            "baseline: template de referencia",
        )
        result = self._git(code_path, "rev-parse", "HEAD")
        if result is None or result.returncode != 0:
            return None
        return result.stdout.strip()

    @staticmethod
    def _git(code_path: Path, *arguments: str) -> subprocess.CompletedProcess | None:
        try:
            return subprocess.run(
                ["git", *arguments],
                cwd=code_path,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return None

    @staticmethod
    def _contain(base: Path, path: Path) -> Path:
        resolved = path.resolve()
        try:
            resolved.relative_to(base)
        except ValueError as error:
            raise ValueError(f"Operacao fora de {base} nao permitida: {path}") from error
        return resolved
