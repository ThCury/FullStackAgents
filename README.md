# FullStackAgents — Squad autônomo de agentes de IA

Trilha B: um squad de agentes que recebe um briefing de cliente e, sozinho, entende o problema, quebra em stories, escreve o código, testa e entrega.

O time humano entra **só no início**, com o briefing.

---

## Rodando em 3 comandos

Nenhuma API key, nenhum MongoDB, nenhum Docker necessário para ver a esteira funcionando.

```bash
cd code/backend && python -m venv .venv && .venv/Scripts/python -m pip install -e ".[dev]"
```

```bash
cd code/backend && .venv/Scripts/uvicorn main:app --reload
```

```bash
cd code/frontend && npm install && npm run dev
```

Abra `http://localhost:5173`, cole o briefing de [docs/briefing-rivexx.md](docs/briefing-rivexx.md) e clique em **acionar squad**.

Os defaults (`SQUAD_LLM=fake`, `SQUAD_PERSISTENCE=memory`) rodam o squad completo com respostas determinísticas de fixture — inclusive o ciclo de reprovação do QA. É o que permite trabalhar em paralelo: quem está no Console não fica bloqueado por quem está afinando prompt, e ninguém queima token testando um roteador.

### Ligando o modo real

```bash
export ANTHROPIC_API_KEY=...
export SQUAD_LLM=anthropic
export SQUAD_PERSISTENCE=mongo   # requer `docker compose up -d mongo`
export SQUAD_SANDBOX=subprocess  # QA executa a suíte de verdade
```

Confira o modo ativo em `GET /health/config` — já economizou tempo de gente depurando "por que não gastou token".

---

## O que existe hoje

| Camada | Estado |
|---|---|
| Grafo do squad (LangGraph) — 7 nós, retrabalho, escalada, checkpointer | ✅ funcionando |
| 4 agentes com contrato de papel validado | ✅ estrutura + prompts; ⚠️ prompts não afinados contra o modelo real |
| Trilha de auditoria em 2 níveis (handoff + prompt cru) | ✅ funcionando |
| Controle de tokens em 3 escopos + escalada por orçamento | ✅ funcionando |
| Export dos 5 entregáveis em Markdown | ✅ funcionando |
| Repositórios Mongo + índices | ✅ escritos; ⚠️ sem teste de integração contra Mongo real |
| Squad Console (timeline, inspector, entregáveis, tokens) | ✅ funcionando |
| Grafo ao vivo com React Flow | ❌ não começado |
| Sandbox Docker (ADR-08) | ❌ `SQUAD_SANDBOX=docker` levanta `NotImplementedError` de propósito |
| Scaffold do app Rivexx + seed sintético | ❌ só o contrato de texto existe |

Um run completo em modo `fake` produz 15 handoffs, 3 stories cobrindo os 3 cenários, 4 ADRs, 4 relatórios de QA (um reprovando) e 4 arquivos de entregável exportados.

---

## Estrutura

```
code/backend/
├── domain/           # entidades, value objects, ports — ZERO framework
├── application/      # casos de uso + renderizadores dos entregáveis
├── agents/           # 1 arquivo por papel + prompts em .md
├── pipeline/         # LangGraph: state, nós, roteadores, grafo
├── factory/          # composição (DI), settings, contrato de scaffold
├── infrastructure/   # LLM, Mongo, workspace, sandbox, observabilidade
├── interfaces/       # FastAPI + SSE
└── tests/            # 52 testes, nenhum toca rede

code/frontend/        # Squad Console (React + TS + Vite)
docs/                 # arquitetura, ADRs, briefing
```

A arquitetura completa e as decisões estão em [docs/arquitetura.md](docs/arquitetura.md). Antes de escrever código, leia [CONTRIBUTING.md](CONTRIBUTING.md) — em especial a regra de dependência, que é aplicada pelo linter.

---

## Comandos do dia a dia

Da raiz do repositório:

```bash
make check
```

Roda lint, format, mypy e testes do backend, mais typecheck e build do frontend. É o mesmo gate do CI — rode antes de abrir PR.

Individualmente, dentro de `code/backend`:

```bash
.venv/Scripts/python -m pytest
```

```bash
.venv/Scripts/python -m ruff check . && .venv/Scripts/python -m mypy .
```

---

## Endpoints

| Método | Rota | Para quê |
|---|---|---|
| `POST` | `/runs` | Aciona o squad. Devolve 202 — a esteira roda em background |
| `GET` | `/runs/{id}` | Status do run |
| `GET` | `/runs/{id}/stream` | SSE ao vivo (orquestração visível) |
| `GET` | `/runs/{id}/timeline` | Trilha de auditoria. `?since_seq=N` traz só o delta |
| `GET` | `/runs/{id}/calls/{call_id}` | Prompt e resposta crus — o Inspector |
| `GET` | `/runs/{id}/deliverables` | Os 5 entregáveis da trilha |
| `GET` | `/runs/{id}/metrics` | Tokens, custo, cache hit rate |
| `POST` | `/runs/{id}/resume` | Retoma um run pausado (`retry` / `skip` / `finish`) |
| `POST` | `/runs/{id}/budget` | Estende o orçamento (decisão humana registrada) |

Docs interativas em `http://localhost:8000/docs`.

---

## Próximos passos

Em ordem de prioridade, seguindo o plano da §12 da arquitetura:

1. **Scaffold do app Rivexx + seed sintético** — sem dados, os cenários de causa raiz e rastreabilidade entregam tela vazia
2. **Sandbox Docker** (ADR-08) — hoje só `subprocess`, com garantias mais fracas
3. **Afinar os prompts** contra o modelo real, medindo custo por agente no Console
4. **Grafo ao vivo** no Console (React Flow)
5. **Teste de integração contra Mongo real** — os repositórios Mongo não têm cobertura
