# Sistema A — Squad de agentes

Implementação de `docs/arquitetura.md`: squad autônomo (BriefingAnalyst → PO →
Dev → QA) orquestrado via LangGraph, Clean Architecture, MongoDB como
backing store único (runs, mensagens, backlog, ADRs, QA, tokens,
checkpoints), sandbox Docker para código gerado.

Este README documenta o que está implementado (Fase 0 + Fase 1 do §12), o
que ficou para depois, e onde esta implementação diverge do documento original
- e por quê.

## Como rodar

```bash
cd code/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # preencha ANTHROPIC_API_KEY

docker-compose up -d   # sobe o MongoDB local (squad_mongo, porta 27017)

cd ..                  # execute a partir de code/, para os imports `backend.*` funcionarem
uvicorn backend.interfaces.http.main:app --reload --port 8000
```

```bash
# dispara o squad com o brief do desafio
curl -X POST http://localhost:8000/runs \
  -H "Content-Type: application/json" \
  -d "{\"briefing\": \"$(cat backend/briefs/rivexx.txt | sed 's/"/\\"/g')\"}"
# -> {"run_id": "...", "status": "queued"}

curl http://localhost:8000/runs/<run_id>   # timeline completa (mensagens, backlog, ADRs, QA)
```

Rodar a mesma chamada de novo com um novo texto de briefing trata a rodada
como incremento: o BriefingAnalyst recebe o histórico de runs anteriores
(`application/use_cases/history.py`) e o estado atual de `code/app`.

Se um run pausar (`status: "awaiting_human"` - orçamento estourado ou 3
reprovações seguidas na mesma story):

```bash
curl -X POST http://localhost:8000/runs/<run_id>/approve-budget -d '{"extra_budget_usd": 5}'
# ou, sem mexer no orçamento, só manda o Dev tentar de novo:
curl -X POST http://localhost:8000/runs/<run_id>/resume -d '{"action": "resume_dev"}'
```

## O que está implementado

- **`domain/`** - entidades (Run, Story, Artifact, ADR, TestReport, AgentMessage,
  NormalizedBriefing), value objects (TokenUsage, AcceptanceCriterion em
  Gherkin), enums, erros (`BudgetExceeded`, `ReworkLimitReached`, `RunNotFound`)
  e os 7 ports (`Agent`, `LLMPort`, `TokenMeterPort`, `CodeWorkspacePort` /
  `ReadOnlyWorkspacePort`, `TestRunnerPort`, `EventBusPort`, os 6
  repositórios). Zero import de framework.
- **`agents/`** - `BaseAgent` (template method: prompt → loop agentic contra
  `LLMPort` → parse → `AgentMessage` obrigatória) e os 4 pacotes concretos
  (`briefing_analyst`, `product_owner`, `developer`, `qa`), cada um com
  `prompt.py` + `schema.py` + `agent.py`. BriefingAnalyst e PO só recebem
  `ReadOnlyWorkspacePort` (ISP - nem por engano escrevem código de produção).
- **`pipeline/`** - `SquadState` com reducers `Annotated[..., operator.add]`
  para os campos append-only, `graph.py` com os 7 nós do §4.2
  (intake/po/dispatch/dev/qa/escalate/integrate) e roteamento condicional
  completo, incluindo o desvio para `escalate` em qualquer nó que estoure
  orçamento.
- **`infrastructure/`** - `AnthropicAdapter` (cache_control ephemeral no
  prefixo estável do system prompt, `output_config.effort` por chamada),
  `BudgetedLLM` (decorator OCP), `MongoTokenMeter` (teto por run - lido do
  próprio documento, para `ApproveBudget` funcionar - e por agente),
  `GitWorkspace`/`ReadOnlyGitWorkspace` (leitura/escrita em `code/app`, cada
  entrega do Dev vira um commit), `DockerTestRunner` (ADR-08: container sem
  rede, timeout).
- **`factory/container.py`** - único lugar que conhece Mongo, Anthropic e
  Docker ao mesmo tempo.
- **`application/use_cases/`** - `StartRun`, `ResumeRun`, `ApproveBudget`,
  `GetRunTimeline`.
- **`interfaces/http/`** - API mínima (`POST /runs`, `GET /runs/{id}`,
  `POST /runs/{id}/resume`, `POST /runs/{id}/approve-budget`), roda em
  processo/porta separados do Rivexx.

Toda a infraestrutura foi validada de ponta a ponta contra um MongoDB real
(container build → checkpointer → grafo compilado com os 8 nós → round-trip
de um `Run` no Mongo) antes de considerar esta fase concluída.

## O que ficou para depois

- **Squad Console (Fase 2)** - decisão explícita com o usuário: esta rodada
  cobre só o backend. `EventBusPort`/`InMemoryEventBus` existem, mas nenhum
  nó chama `get_stream_writer()` ainda - a timeline granular ("Dev Agent
  escrevendo `NCForm.tsx`") só faz sentido implementar junto com um consumidor
  real (o Console).
- **Scaffold curado do Rivexx + seed sintético (Fase 4)** - decisão explícita
  com o usuário: Dev Agent parte de `code/app` vazio. Sem o scaffold e o seed
  descritos em §7.2/§11, os cenários 2 e 3 (causa raiz assistida,
  rastreabilidade) ficam sem dado para demonstrar valor na primeira
  execução.
- **Playwright/e2e** - `TestRunnerPort.run_frontend_tests` chama `npm test`
  dentro do container; não há harness Playwright configurado ainda (depende
  do scaffold do frontend existir).
- **`Send` / fan-out paralelo** - decisão explícita com o usuário: fan-out
  sequencial por ora (`dispatch` pega uma story por vez).

## Onde isto diverge do `docs/arquitetura.md` (e por quê)

1. **Modelo por agente, não `claude-opus-5` fixo (ADR-05).** Decisão
   explícita do usuário: mantido `claude-sonnet-5` como padrão, configurável
   por agente via env var. O dial de custo (`effort`) é aplicado do mesmo
   jeito.
2. **`MongoDBSaver`, não `AsyncMongoDBSaver`/`langgraph.checkpoint.mongodb.aio`.**
   O import citado no documento não existe em
   `langgraph-checkpoint-mongodb==0.4.0` (verificado em runtime) - a lib
   unificou sync/async numa única classe `MongoDBSaver` (métodos `get`/`put`
   e `aget`/`aput` na mesma classe). O construtor dela exige um
   `pymongo.MongoClient` síncrono, não o `AsyncIOMotorClient` usado pelos
   repositórios - por isso `pipeline/checkpointer.py` mantém seu próprio
   client, mesmo apontando para o mesmo banco. Ver o docstring do arquivo.
3. **`output_config.format` (structured output) não está ligado ao loop de
   tools ainda.** Os agentes recebem instrução para responder só com JSON e
   isso é parseado (`agents/utils.extract_json`), igual ao pipeline anterior.
   Os schemas de saída já existem em cada `schema.py` - dá pra ligar
   `output_config.format` neles depois, mas eu não tinha como validar com
   segurança a interação exata entre `tools` ativo e `format` forçado em
   todas as iterações do loop sem rodar de verdade contra a API, então
   preferi não arriscar quebrar o parsing silenciosamente.
