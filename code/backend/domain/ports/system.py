"""Ports de infraestrutura ambiental — tempo e identidade.

Parecem triviais, mas injetá-las é o que torna o squad testável de forma
determinística: com `FrozenClock` + `SequentialIdGenerator`, um run inteiro
produz exatamente o mesmo resultado em toda execução, e dá para asseverar a
trilha de auditoria inteira em teste.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class ClockPort(Protocol):
    def now(self) -> datetime: ...


@runtime_checkable
class IdGeneratorPort(Protocol):
    def new_id(self, prefix: str = "") -> str: ...
