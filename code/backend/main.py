"""Entrypoint da API do Squad.

    uvicorn main:app --reload

Nada de lógica aqui: monta a app, injeta o container no `lifespan`, registra os
routers. Se você precisar mudar comportamento do squad, o lugar é
`factory/container.py` (composição) ou a camada correspondente — não este
arquivo.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from factory.container import build_container
from factory.settings import Settings
from interfaces.http.routers import health, runs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger("squad")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = Settings()
    logger.info(
        "subindo squad — llm=%s persistence=%s sandbox=%s",
        settings.llm.value,
        settings.persistence.value,
        settings.sandbox.value,
    )
    if settings.llm.value == "fake":
        logger.warning(
            "modo FAKE: respostas determinísticas de fixture, nenhum token gasto. "
            "Para rodar de verdade: SQUAD_LLM=anthropic + ANTHROPIC_API_KEY."
        )

    container = await build_container(settings)
    app.state.container = container
    try:
        yield
    finally:
        await container.aclose()
        logger.info("squad encerrado")


def create_app() -> FastAPI:
    settings = Settings()
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(runs.router)
    return app


app = create_app()
