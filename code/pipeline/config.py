"""Configuração central do pipeline: chaves de API, modelos por agente e paths.

Cada agente pode ter seu próprio modelo via env var (ex: DEV_MODEL), caindo no
PIPELINE_MODEL padrão quando não especificado.
"""
from __future__ import annotations

import os
from pathlib import Path

PIPELINE_ROOT = Path(__file__).resolve().parent

try:
    from dotenv import load_dotenv

    # Caminho explícito (em vez de load_dotenv() sem argumento): sem isso,
    # python-dotenv resolve o .env a partir do frame de quem chamou ou, na
    # falta de um frame com arquivo real, do cwd do processo. No Windows, o
    # worker do `uvicorn --reload` sobe via multiprocessing em modo spawn, que
    # não tem um __main__.__file__ real - dotenv cai pro cwd (`code/`) e nunca
    # acha `code/pipeline/.env`, que é uma subpasta, não um ancestral.
    load_dotenv(PIPELINE_ROOT / ".env")
except ImportError:
    pass

CODE_ROOT = PIPELINE_ROOT.parent
APP_ROOT = CODE_ROOT / "app"
ARTIFACTS_DIR = PIPELINE_ROOT / "artifacts"

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

DEFAULT_MODEL = os.environ.get("PIPELINE_MODEL", "claude-sonnet-5")
ANALYST_MODEL = os.environ.get("ANALYST_MODEL", DEFAULT_MODEL)
PO_MODEL = os.environ.get("PO_MODEL", DEFAULT_MODEL)
DEV_MODEL = os.environ.get("DEV_MODEL", DEFAULT_MODEL)
QA_MODEL = os.environ.get("QA_MODEL", DEFAULT_MODEL)

MAX_REVISIONS = int(os.environ.get("PIPELINE_MAX_REVISIONS", "2"))
MAX_TOOL_ITERATIONS = int(os.environ.get("PIPELINE_MAX_TOOL_ITERATIONS", "20"))
