"""Port de eventos ao vivo. A implementação real publica em memória (fila
asyncio por run_id) e é consumida pelo endpoint SSE - ver
interfaces/sse/stream.py. Troca de transporte (ex: Redis pub/sub) fica
isolada aqui dentro."""
from __future__ import annotations

from typing import Any, AsyncIterator, Protocol


class EventBusPort(Protocol):
    async def publish(self, run_id: str, mode: str, chunk: Any) -> None: ...

    def subscribe(self, run_id: str) -> AsyncIterator[tuple[str, Any]]: ...
