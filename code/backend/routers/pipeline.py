"""Endpoint que expõe o squad de agentes por HTTP.

`POST /api/demandas/stream` recebe a demanda digitada no frontend e devolve um
stream Server-Sent Events (SSE): uma mensagem por vez, na ordem em que os
agentes se comunicam, seguida de um evento final `done` com o resumo da
execução. Usamos POST (em vez de GET, que é o que o EventSource nativo do
browser exige) porque a demanda pode ser longa e o frontend consome o stream
via `fetch` + `ReadableStream`, não via `EventSource`.

A chamada ao pipeline é bloqueante (várias idas ao LLM em sequência), então
roda em uma thread separada; o resultado é repassado ao loop de eventos
assíncrono do FastAPI por uma `asyncio.Queue`.
"""
from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from pipeline.stream import run_pipeline_stream

router = APIRouter()


class DemandaRequest(BaseModel):
    demand: str
    max_revisions: int | None = None


def _format_sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


@router.post("/demandas/stream")
async def stream_demanda(payload: DemandaRequest) -> StreamingResponse:
    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def worker() -> None:
        try:
            for event in run_pipeline_stream(payload.demand, max_revisions=payload.max_revisions):
                asyncio.run_coroutine_threadsafe(queue.put(event), loop)
        except Exception as exc:  # pragma: no cover - repassa erro do pipeline ao cliente
            asyncio.run_coroutine_threadsafe(queue.put({"type": "error", "data": str(exc)}), loop)
        finally:
            asyncio.run_coroutine_threadsafe(queue.put(None), loop)

    loop.run_in_executor(None, worker)

    async def event_generator() -> AsyncIterator[str]:
        while True:
            event = await queue.get()
            if event is None:
                break
            yield _format_sse(event)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
