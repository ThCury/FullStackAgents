"""Entrypoint FastAPI do Sistema A (squad). Roda separado do Sistema B
(Rivexx) - processos, portas e bancos diferentes (§1). Uma única instância de
Container é montada no startup e reaproveitada por toda a vida do processo."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ...factory.container import Container
from ...infrastructure.persistence.mongo.client import ensure_indexes
from ...pipeline.checkpointer import close_checkpointer
from .routers import runs, dashboard


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_indexes()
    app.state.container = Container()
    app.state.background_tasks = set()
    yield
    close_checkpointer()


app = FastAPI(title="Squad Console API - Sistema A", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(dashboard.router)
app.include_router(runs.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
