"""EventBus em memória para o stream SSE do Console.

Decisão deliberada: **fire-and-forget com fila limitada**. Se um cliente do
Console for lento, ou se ninguém estiver assistindo, o evento é descartado — o
squad nunca bloqueia por causa da UI. Perder um frame de animação é aceitável;
travar a esteira de agentes por backpressure de browser não é.

A trilha durável não é isto — é a coleção `agent_messages`. O Console reconecta
e recarrega o histórico dela. Este barramento é só o tempo real.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from contextlib import suppress

from domain.ports.observability import SquadEvent

_QUEUE_MAX = 1_000


class InMemoryEventBus:
    def __init__(self, queue_max: int = _QUEUE_MAX) -> None:
        self._queue_max = queue_max
        self._subscribers: dict[str, set[asyncio.Queue[SquadEvent | None]]] = defaultdict(set)

    async def publish(self, event: SquadEvent) -> None:
        for queue in tuple(self._subscribers.get(event.run_id, ())):
            # Consumidor lento: descarta o evento e segue. Ver docstring do módulo —
            # travar a esteira de agentes por backpressure de browser não é opção.
            with suppress(asyncio.QueueFull):
                queue.put_nowait(event)

    def subscribe(self, run_id: str) -> EventSubscription:
        queue: asyncio.Queue[SquadEvent | None] = asyncio.Queue(maxsize=self._queue_max)
        self._subscribers[run_id].add(queue)
        return EventSubscription(self, run_id, queue)

    def unsubscribe(self, run_id: str, queue: asyncio.Queue[SquadEvent | None]) -> None:
        self._subscribers[run_id].discard(queue)
        if not self._subscribers[run_id]:
            self._subscribers.pop(run_id, None)


class EventSubscription:
    """Async iterator de eventos de um run. `close()` encerra o `async for`."""

    def __init__(
        self,
        bus: InMemoryEventBus,
        run_id: str,
        queue: asyncio.Queue[SquadEvent | None],
    ) -> None:
        self._bus = bus
        self._run_id = run_id
        self._queue = queue
        self._closed = False

    def __aiter__(self) -> EventSubscription:
        return self

    async def __anext__(self) -> SquadEvent:
        if self._closed:
            raise StopAsyncIteration
        event = await self._queue.get()
        if event is None:
            raise StopAsyncIteration
        return event

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._bus.unsubscribe(self._run_id, self._queue)
        with suppress(asyncio.QueueFull):
            self._queue.put_nowait(None)  # sentinela: encerra o `async for`
