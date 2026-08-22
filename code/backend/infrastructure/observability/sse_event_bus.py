"""EventBusPort em memória (um processo). Suficiente para rodar local; troca
por Redis pub/sub fica isolada aqui se algum dia precisar de múltiplos
workers. Consumido pelo endpoint SSE em interfaces/sse/stream.py - o Console
(Fase 2, ainda não construído) é quem vai renderizar isso."""
from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, AsyncIterator


class InMemoryEventBus:
    def __init__(self):
        self._queues: dict[str, list[asyncio.Queue]] = defaultdict(list)

    async def publish(self, run_id: str, mode: str, chunk: Any) -> None:
        for queue in list(self._queues.get(run_id, [])):
            await queue.put((mode, chunk))

    async def subscribe(self, run_id: str) -> AsyncIterator[tuple[str, Any]]:
        queue: asyncio.Queue = asyncio.Queue()
        self._queues[run_id].append(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._queues[run_id].remove(queue)
