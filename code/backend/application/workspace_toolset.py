from __future__ import annotations

import fnmatch
import re

from domain.models.tool_call import ToolCall
from domain.models.tool_definition import ToolDefinition
from domain.models.tool_result import ToolResult
from domain.ports.workspace_manager import WorkspaceManager

MAX_GREP_MATCHES = 60
MAX_LISTED_FILES = 400


class ToolViolationError(RuntimeError):
    """O agente insistiu em operações inválidas além do tolerado."""


class WorkspaceToolset:
    """Expõe o workspace ao modelo como ferramentas.

    `writable=False` entrega apenas leitura: é assim que o planner explora o
    template sem poder alterá-lo.
    """

    def __init__(
        self,
        workspace_manager: WorkspaceManager,
        workspace: dict,
        writable: bool,
        max_violations: int = 10,
    ) -> None:
        self._manager = workspace_manager
        self._workspace = workspace
        self._writable = writable
        self._max_violations = max_violations
        self._violations = 0
        self._writes: list[dict[str, str]] = []

    @property
    def writes(self) -> list[dict[str, str]]:
        """Trilha das escritas efetivadas, na ordem em que aconteceram."""
        return list(self._writes)

    def definitions(self) -> list[ToolDefinition]:
        tools = [
            ToolDefinition(
                name="list_files",
                description=(
                    "Lista os arquivos do projeto, em caminhos relativos à raiz do código. "
                    "Use o parâmetro pattern para filtrar (ex.: 'backend/**/*.py')."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Glob opcional de filtro.",
                        }
                    },
                },
            ),
            ToolDefinition(
                name="read_file",
                description="Lê o conteúdo completo de um arquivo do projeto.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Caminho relativo à raiz do código.",
                        }
                    },
                    "required": ["path"],
                },
            ),
            ToolDefinition(
                name="grep",
                description=(
                    "Busca uma expressão regular no conteúdo dos arquivos e devolve "
                    "as ocorrências como caminho:linha:conteúdo."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "Expressão regular."},
                        "path_pattern": {
                            "type": "string",
                            "description": "Glob opcional para limitar os arquivos.",
                        },
                    },
                    "required": ["pattern"],
                },
            ),
        ]
        if not self._writable:
            return tools
        return tools + [
            ToolDefinition(
                name="write_file",
                description=(
                    "Cria ou substitui um arquivo com o conteúdo completo informado. "
                    "Não existe escrita parcial: envie o arquivo inteiro."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Caminho relativo à raiz do código.",
                        },
                        "content": {"type": "string", "description": "Conteúdo completo."},
                    },
                    "required": ["path", "content"],
                },
            ),
            ToolDefinition(
                name="delete_file",
                description="Remove um arquivo existente do projeto.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Caminho relativo à raiz do código.",
                        }
                    },
                    "required": ["path"],
                },
            ),
        ]

    def execute(self, call: ToolCall) -> ToolResult:
        handlers = {
            "list_files": self._list_files,
            "read_file": self._read_file,
            "grep": self._grep,
            "write_file": self._write_file,
            "delete_file": self._delete_file,
        }
        handler = handlers.get(call.name)
        if handler is None or (not self._writable and call.name in {"write_file", "delete_file"}):
            return self._failure(call, f"Ferramenta indisponível: {call.name}")
        try:
            return ToolResult(call_id=call.id, name=call.name, content=handler(call.arguments))
        except (ValueError, KeyError, FileNotFoundError, OSError, re.error) as error:
            return self._failure(call, str(error))

    def _failure(self, call: ToolCall, message: str) -> ToolResult:
        self._violations += 1
        if self._violations > self._max_violations:
            raise ToolViolationError(
                f"Limite de {self._max_violations} chamadas inválidas excedido. "
                f"Última falha em {call.name}: {message}"
            )
        return ToolResult(
            call_id=call.id, name=call.name, content=f"ERRO: {message}", is_error=True
        )

    def _list_files(self, arguments: dict) -> str:
        paths = self._manager.code_tree(self._workspace)
        pattern = (arguments.get("pattern") or "").strip()
        if pattern:
            paths = [path for path in paths if fnmatch.fnmatch(path, pattern)]
        if not paths:
            return "Nenhum arquivo encontrado."
        listed = paths[:MAX_LISTED_FILES]
        suffix = (
            f"\n[... {len(paths) - MAX_LISTED_FILES} arquivos omitidos; refine o pattern ...]"
            if len(paths) > MAX_LISTED_FILES
            else ""
        )
        return "\n".join(listed) + suffix

    def _read_file(self, arguments: dict) -> str:
        return self._manager.read_code(self._workspace, self._required(arguments, "path"))

    def _grep(self, arguments: dict) -> str:
        expression = re.compile(self._required(arguments, "pattern"))
        path_pattern = (arguments.get("path_pattern") or "").strip()
        matches: list[str] = []
        for path in self._manager.code_tree(self._workspace):
            if path_pattern and not fnmatch.fnmatch(path, path_pattern):
                continue
            try:
                content = self._manager.read_code(self._workspace, path)
            except (ValueError, OSError):
                continue
            for number, line in enumerate(content.splitlines(), start=1):
                if expression.search(line):
                    matches.append(f"{path}:{number}:{line.strip()[:200]}")
                    if len(matches) >= MAX_GREP_MATCHES:
                        return "\n".join(matches) + "\n[... busca truncada ...]"
        return "\n".join(matches) if matches else "Nenhuma ocorrência encontrada."

    def _write_file(self, arguments: dict) -> str:
        path = self._required(arguments, "path")
        content = arguments.get("content")
        if not isinstance(content, str):
            raise ValueError("O parâmetro content é obrigatório e deve ser texto.")
        existed = path in set(self._manager.code_tree(self._workspace))
        self._manager.write_code(self._workspace, path, content)
        action = "update" if existed else "create"
        self._writes.append({"path": path, "action": action})
        lines = content.count("\n") + 1
        return f"OK: {action} de {path} ({lines} linhas gravadas)."

    def _delete_file(self, arguments: dict) -> str:
        path = self._required(arguments, "path")
        self._manager.delete_code(self._workspace, path)
        self._writes.append({"path": path, "action": "delete"})
        return f"OK: {path} removido."

    @staticmethod
    def _required(arguments: dict, name: str) -> str:
        value = arguments.get(name)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"O parâmetro {name} é obrigatório.")
        return value.strip()
