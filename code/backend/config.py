"""Configuração central. Único lugar (além de factory/container.py) que lê
variáveis de ambiente."""
from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

BACKEND_ROOT = Path(__file__).resolve().parent
CODE_ROOT = BACKEND_ROOT.parent
APP_ROOT = CODE_ROOT / "app"  # workspace do Sistema B (Rivexx) - nunca compartilha banco/processo com o Sistema A

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ADR-05 pede claude-opus-5 para todos os agentes. Optamos por manter o modelo
# configurável por agente (decisão registrada com o usuário) em vez de fixar
# opus-5 - ver docs/adr/0001-modelo-configuravel-por-agente.md.
DEFAULT_MODEL = os.environ.get("PIPELINE_MODEL", "claude-sonnet-5")
ANALYST_MODEL = os.environ.get("ANALYST_MODEL", DEFAULT_MODEL)
PO_MODEL = os.environ.get("PO_MODEL", DEFAULT_MODEL)
DEV_MODEL = os.environ.get("DEV_MODEL", DEFAULT_MODEL)
QA_MODEL = os.environ.get("QA_MODEL", DEFAULT_MODEL)

# Dial de custo por agente (§8.4) - "low" | "medium" | "high" | "xhigh".
ANALYST_EFFORT = os.environ.get("ANALYST_EFFORT", "medium")
PO_EFFORT = os.environ.get("PO_EFFORT", "high")
DEV_EFFORT = os.environ.get("DEV_EFFORT", "high")
QA_EFFORT = os.environ.get("QA_EFFORT", "medium")

# Teto de tokens de saída por chamada. O thinking adaptativo (ligado por
# padrão) consome deste MESMO orçamento antes do texto visível - baixo demais
# trunca a resposta silenciosamente. PO e Dev produzem JSON grande (backlog
# com várias stories em Gherkin; ADR com alternativas) e por isso têm piso
# maior. PO e Dev não têm mais teto de escopo (stories amplas / arquitetura
# livre no Dev), por isso os pisos aqui são mais folgados do que o mínimo
# histórico de 16000/24000 - ajuste via env se ainda truncar em backlogs ou
# implementações grandes.
ANALYST_MAX_TOKENS = int(os.environ.get("ANALYST_MAX_TOKENS", "8000"))
PO_MAX_TOKENS = int(os.environ.get("PO_MAX_TOKENS", "32000"))
# Dev usa tool calls (write_file) cujo conteúdo do arquivo inteiro conta como
# tokens de saída da MESMA chamada - arquivos maiores exigem mais headroom
# que o JSON final de decisão sozinho pediria.
DEV_MAX_TOKENS = int(os.environ.get("DEV_MAX_TOKENS", "32000"))
QA_MAX_TOKENS = int(os.environ.get("QA_MAX_TOKENS", "8000"))

MAX_REVISIONS = int(os.environ.get("PIPELINE_MAX_REVISIONS", "3"))
MAX_TOOL_ITERATIONS = int(os.environ.get("PIPELINE_MAX_TOOL_ITERATIONS", "20"))

# Dev e QA fazem mais tool calls que Analyst/PO (ler/escrever arquivos, rodar
# testes, corrigir e rodar de novo). O Dev agora tem liberdade de arquitetura
# (múltiplos arquivos/camadas em vez de um único arquivo consolidado), o que
# exige mais iterações de write_file por story - teto elevado para acomodar
# isso sem cortar o trabalho pela metade.
DEV_MAX_TOOL_ITERATIONS = int(os.environ.get("DEV_MAX_TOOL_ITERATIONS", "40"))
QA_MAX_TOOL_ITERATIONS = int(os.environ.get("QA_MAX_TOOL_ITERATIONS", "15"))

# ADR-01/03: MongoDB é o backing store do Sistema A (squad_db) - runs,
# mensagens, stories, ADRs, QA, ledger de tokens, checkpoints do LangGraph.
MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB = os.environ.get("MONGODB_DB", "squad_db")

# Orçamento (§8.3, decisão do usuário: $5/run, medir por agente também).
BUDGET_PER_RUN_USD = float(os.environ.get("BUDGET_PER_RUN_USD", "5.0"))
BUDGET_PER_AGENT_USD = float(os.environ.get("BUDGET_PER_AGENT_USD", "3.0"))

# Preços de referência (claude-sonnet-5) para o ledger de custo - ajustar via
# env se a tabela de preços mudar. Em USD por milhão de tokens.
PRICE_INPUT_PER_MTOK = float(os.environ.get("PRICE_INPUT_PER_MTOK", "3.0"))
PRICE_OUTPUT_PER_MTOK = float(os.environ.get("PRICE_OUTPUT_PER_MTOK", "15.0"))

# ADR-08: sandbox Docker para execução de código gerado pelo Dev Agent.
# Não negociável: código escrito por LLM nunca roda no host, sem rede, com timeout.
DOCKER_SANDBOX_BACKEND_IMAGE = os.environ.get("DOCKER_SANDBOX_BACKEND_IMAGE", "python:3.11-slim")
DOCKER_SANDBOX_FRONTEND_IMAGE = os.environ.get("DOCKER_SANDBOX_FRONTEND_IMAGE", "node:20-slim")
DOCKER_SANDBOX_TIMEOUT_SECONDS = int(os.environ.get("DOCKER_SANDBOX_TIMEOUT_SECONDS", "180"))
