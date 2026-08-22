"""Implementações de `ClockPort` e `IdGeneratorPort`.

As variantes determinísticas não são só para teste: com elas, um run inteiro é
reproduzível, o que permite asseverar a trilha de auditoria completa e comparar
duas execuções do squad.
"""

from __future__ import annotations

from datetime import UTC, datetime
from itertools import count
from uuid import uuid4


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class FrozenClock:
    """Relógio parado, avançável manualmente. Para testes."""

    def __init__(self, start: datetime | None = None, step_seconds: float = 0.0) -> None:
        self._current = start or datetime(2026, 1, 1, tzinfo=UTC)
        self._step = step_seconds

    def now(self) -> datetime:
        current = self._current
        if self._step:
            self.advance(self._step)
        return current

    def advance(self, seconds: float) -> None:
        from datetime import timedelta

        self._current = self._current + timedelta(seconds=seconds)


class UuidGenerator:
    def new_id(self, prefix: str = "") -> str:
        raw = uuid4().hex[:12]
        return f"{prefix}_{raw}" if prefix else raw


class SequentialIdGenerator:
    """Ids previsíveis (`story_1`, `story_2`, ...). Para testes e para o run de
    referência gravado da demo."""

    def __init__(self) -> None:
        self._counters: dict[str, count[int]] = {}

    def new_id(self, prefix: str = "") -> str:
        key = prefix or "id"
        counter = self._counters.setdefault(key, count(1))
        return f"{key}_{next(counter)}"
