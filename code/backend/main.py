"""Ponto de entrada do backend: expõe o pipeline de agentes por HTTP para o
frontend consumir.

Como o pacote `pipeline` é irmão de `backend` dentro de `code/`, isso precisa
rodar com `code/` como raiz do sys.path - por isso o comando de execução é
sempre a partir de `code/` (ver README do backend):

    cd code
    uvicorn backend.main:app --reload --port 8000
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .routers.pipeline import router as pipeline_router

app = FastAPI(title="Rivexx Squad Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.FRONTEND_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pipeline_router, prefix="/api")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
