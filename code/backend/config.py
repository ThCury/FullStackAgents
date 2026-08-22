"""Configuração do backend: origem liberada para CORS e porta.

A key da Anthropic NÃO mora aqui - fica em `code/pipeline/.env` e é lida pelo
próprio `pipeline.config` quando o backend importa o pacote `pipeline`. Este
`.env` (opcional) é só para parâmetros do servidor HTTP em si.
"""
from __future__ import annotations

import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

_DEFAULT_ORIGINS = "http://localhost:3000,http://localhost:3001"
FRONTEND_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("FRONTEND_ORIGIN", _DEFAULT_ORIGINS).split(",")
    if origin.strip()
]
BACKEND_PORT = int(os.environ.get("BACKEND_PORT", "8000"))
