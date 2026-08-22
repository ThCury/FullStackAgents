"""Port de acesso ao código gerado (code/app). Só o Dev Agent recebe a
capacidade de escrita (ISP: QA recebe uma view read-only do mesmo port, ver
factory/container.py)."""
from __future__ import annotations

from typing import Protocol


class CodeWorkspacePort(Protocol):
    def read_file(self, rel_path: str) -> str: ...

    def write_file(self, rel_path: str, content: str) -> str: ...

    def list_dir(self, rel_path: str = ".") -> str: ...

    def commit(self, message: str) -> str:
        """Cria um commit git com as alterações pendentes. Retorna o SHA
        (ou uma string vazia se não houver nada para commitar)."""
        ...


class ReadOnlyWorkspacePort(Protocol):
    """Mesma leitura do CodeWorkspacePort, sem write_file/commit - usada pelo
    BriefingAnalyst e pelo PO, que não podem escrever código de produção."""

    def read_file(self, rel_path: str) -> str: ...

    def list_dir(self, rel_path: str = ".") -> str: ...
